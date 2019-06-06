from PyQt5 import QtCore
from datetime import datetime
from nsls2ptycho.core.ptycho_param import Param
import sys, os
import pickle     # dump param into disk
import subprocess # call mpirun from shell
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK
import numpy as np
import traceback
try:
    from nsls2ptycho.core.HXN_databroker import load_metadata, save_data
except ImportError as ex:
    print('[!] Unable to import core.HXN_databroker packages some features will '
          'be unavailable')
    print('[!] (import error: {})'.format(ex))
from nsls2ptycho.core.utils import use_mpi_machinefile, set_flush_early


class PtychoReconWorker(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(int, object) # (interation number, chi arrays)
    process = None # subprocess 

    def __init__(self, param:Param=None, parent=None):
        super().__init__(parent)
        self.param = param
        self.return_value = None

    def _parse_message(self, tokens):
        def _parser(current, upper_limit, target_list):
            for j in range(upper_limit):
                target_list.append(float(tokens[current+2+j]))
    
        # assuming tokens (stdout line) is split but not yet processed
        it = int(tokens[2])
        
        # first remove brackets
        empty_index_list = []
        for i, token in enumerate(tokens):
            tokens[i] = token.replace('[', '').replace(']', '')
            if tokens[i] == '':
                empty_index_list.append(i)
        counter = 0
        for i in empty_index_list:
            del tokens[i-counter]
            counter += 1

        # next parse based on param and the known format
        prb_list = []
        obj_list = []
        for i, token in enumerate(tokens):
            if token == 'probe_chi':
                if self.param.mode_flag:
                    _parser(i, self.param.prb_mode_num, prb_list)
                #elif self.param.multislice_flag: 
                #TODO: maybe multislice will have multiple prb in the future?
                else:
                    _parser(i, 1, prb_list)
            if token == 'object_chi':
                if self.param.mode_flag:
                    _parser(i, self.param.obj_mode_num, obj_list)
                elif self.param.multislice_flag:
                    _parser(i, self.param.slice_num, obj_list)
                else:
                    _parser(i, 1, obj_list)

        # return a dictionary
        result = {'probe_chi':prb_list, 'object_chi':obj_list}

        return it, result

    def _test_stdout_completeness(self, stdout):
        counter = 0
        for token in stdout:
            if token == '=':
                counter += 1

        return counter

    def _parse_one_line(self):
        stdout_2 = self.process.stdout.readline().decode('utf-8')
        print(stdout_2, end='') # because the line already ends with '\n'

        return stdout_2.split()

    def recon_api(self, param:Param, update_fcn=None):
        # "1" is just a placeholder to be overwritten soon
        mpirun_command = ["mpirun", "-n", "1", "python", "-W", "ignore", "-m","nsls2ptycho.core.ptycho.recon_ptycho_gui"]

        if param.mpi_file_path == '':
            if param.gpu_flag:
                mpirun_command[2] = str(len(param.gpus))
            else:
                mpirun_command[2] = str(param.processes) if param.processes > 1 else str(1)
        else:
            # regardless if GPU is used or not --- trust users to know this
            mpirun_command = use_mpi_machinefile(mpirun_command, param.mpi_file_path)

        mpirun_command = set_flush_early(mpirun_command)
                
        try:
            self.return_value = None
            with subprocess.Popen(mpirun_command,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  env=dict(os.environ, mpi_warn_on_fork='0')) as run_ptycho:
                self.process = run_ptycho # register the subprocess

                # idea: if we attempts to readline from an empty pipe, it will block until 
                # at least one line is piped in. However, stderr is ususally empty, so reading
                # from it is very likely to block the output until the subprocess ends, which 
                # is bad. Thus, we want to set the O_NONBLOCK flag for stderr, see
                # http://eyalarubas.com/python-subproc-nonblock.html 
                #
                # Note that it is unclear if readline in Python 3.5+ is guaranteed safe with 
                # non-blocking pipes or not. See https://bugs.python.org/issue1175#msg56041 
                # and https://stackoverflow.com/questions/375427/
                # If this is a concern, using the asyncio module could be a safer approach?
                # One could also process stdout in one loop and then stderr in another, which
                # will not have the blocking issue.
                flags = fcntl(run_ptycho.stderr, F_GETFL) # first get current stderr flags
                fcntl(run_ptycho.stderr, F_SETFL, flags | O_NONBLOCK)

                while True:
                    stdout = run_ptycho.stdout.readline()
                    stderr = run_ptycho.stderr.readline() # without O_NONBLOCK this will very likely block
                    if (run_ptycho.poll() is not None) and (stdout==b'') and (stderr==b''):
                        break

                    if stdout:
                        stdout = stdout.decode('utf-8')
                        print(stdout, end='') # because the line already ends with '\n'
                        stdout = stdout.split()
                        if len(stdout) > 2 and stdout[0] == "[INFO]" and update_fcn is not None:
                            # TEST: check if stdout is complete by examining the number of "="
                            # TODO: improve this ugly hack...
                            while True:
                                counter = self._test_stdout_completeness(stdout)
                                if counter == 3:
                                    break
                                elif counter < 3:
                                    stdout += self._parse_one_line()
                                else: # counter > 3, we read one more line!
                                    raise Exception("parsing error")
                          
                            it, result = self._parse_message(stdout)
                            #print(result['probe_chi'])
                            update_fcn(it+1, result)
                        elif stdout[0] == "shared" and update_fcn is not None:
                            update_fcn(-1, "init_mmap")

                    if stderr:
                        stderr = stderr.decode('utf-8')
                        print(stderr, file=sys.stderr, end='')

                # get the return value 
                self.return_value = run_ptycho.poll()

            if self.return_value != 0:
                message = "At least one MPI process returned a nonzero value, so the whole job is aborted.\n"
                message += "If you did not manually terminate it, consult the Traceback above to identify the problem."
                raise Exception(message)
        except Exception as ex:
            traceback.print_exc()
            #print(ex, file=sys.stderr)
            #raise ex
        finally:
            # clean up temp file
            filepath = param.working_directory + "/." + param.shm_name + ".txt"
            if os.path.isfile(filepath):
                os.remove(filepath)

    def run(self):
        print('Ptycho thread started')
        try:
            self.recon_api(self.param, self.update_signal.emit)
        except IndexError:
            print("[ERROR] IndexError --- most likely a wrong MPI machine file is given?", file=sys.stderr)
        except:
            # whatever happened in the MPI processes will always (!) generate traceback,
            # so do nothing here
            pass
        else:
            # let preview window load results
            if self.param.preview_flag and self.return_value == 0:
                self.update_signal.emit(self.param.n_iterations+1, None)
        finally:
            print('finally?')

    def kill(self):
        if self.process is not None:
            print('killing the subprocess...')
            self.process.terminate()
            self.process.wait()


# a worker that does the rest of hard work for us
class HardWorker(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(int, object) # connect to MainWindow???
    def __init__(self, task=None, *args, parent=None):
        super().__init__(parent)
        self.task = task
        self.args = args
        self.exception_handler = None
        #self.update_signal = QtCore.pyqtSignal(int, object) # connect to MainWindow???

    def run(self):
        try:
            if self.task == "save_h5":
                self._save_h5(self.update_signal.emit)
            elif self.task == "fetch_data":
                self._fetch_data(self.update_signal.emit)
            # TODO: put other heavy lifting works here
            # TODO: consider merge other worker threads to this one?
        except ValueError as ex:
            # from _fetch_data(), print it and quit
            print(ex, file=sys.stderr)
            print("[ERROR] possible reason: no image available for the selected detector/scan", file=sys.stderr)
        except Exception as ex:
            # use MainWindow's exception handler
            if self.exception_handler is not None:
                self.exception_handler(ex)

    def kill(self):
        pass

    def _save_h5(self, update_fcn=None):
        '''
        args = [db, param, scan_num, roi_width, roi_height, cx, cy, threshold, bad_pixels]
        '''
        print("saving data to h5, this may take a while...")
        save_data(*self.args)
        print("h5 saved.")

    def _fetch_data(self, update_fcn=None):
        '''
        args = [db, scan_id, det_name]
        '''
        if update_fcn is not None:
            print("loading begins, this may take a while...", end='')
            metadata = load_metadata(*self.args)

            # sanity checks
            if metadata['nz'] == 0:
                raise ValueError("nz = 0")
            #print("databroker connected, parsing experimental parameters...", end='')
            # get nx and ny by looking at the first image
            img = self.args[0].reg.retrieve(metadata['mds_table'].iat[0])[0]
            nx, ny = img.shape # can also give a ValueError; TODO: come up a better way!
            metadata['nx'] = nx
            metadata['ny'] = ny

            update_fcn(0, metadata) # 0 is just a placeholder


class PtychoReconFakeWorker(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(int, object)

    def __init__(self, param:Param=None, parent=None):
        super().__init__(parent)
        self.param = param

    def _get_random_message(self, it):
        object_chi = np.random.random()
        probe_chi = np.random.random()
        diff_chi = np.random.random()
        return '[INFO] DM {:d} object_chi = {:f} probe_chi = {:f} diff_chi = {:f}'.format(
            it, object_chi, probe_chi, diff_chi)

    def _array_to_str(self, arr):
        arrstr = ''
        for v in arr: arrstr += '{:f} '.format(v)
        return arrstr

    def _get_random_message_multi(self, it):
        object_chi = np.random.random(4)
        probe_chi = np.random.random(4)
        diff_chi = np.random.random(4)

        object_chi_str = self._array_to_str(object_chi)
        probe_chi_str = self._array_to_str(probe_chi)
        diff_chi_str = self._array_to_str(diff_chi)

        return '[INFO] DM {:d} object_chi = {:s} probe_chi = {:s} diff_chi = {:s}'.format(
            it, object_chi_str, probe_chi_str, diff_chi_str)


    def _parse_message(self, message):
        message = str(message).replace('[', '').replace(']', '')

        tokens = message.split()
        id, alg, it = tokens[0], tokens[1], int(tokens[2])

        metric_tokens = tokens[3:]
        metric = {}
        name = 'Unknown'
        data = []

        for i in range(len(metric_tokens)):
            token = str(metric_tokens[i])

            if token == '=': continue

            if i < len(metric_tokens) - 2 and metric_tokens[i+1] == '=':
                if len(data): metric[name] = list(data)
                name = token
                data = []
                continue

            data.append(float(token))

        if len(data):
            metric[name] = data

        return id, alg, it, metric

    def run(self):
        from time import sleep
        update_fcn = self.update_signal.emit
        for it in range(self.param.n_iterations):

            message = self._get_random_message(it)
            _id, _alg, _it, _metric = self._parse_message(message)

            update_fcn(_it+1, _metric)
            sleep(.1)

        print("finished")

    def kill(self):
        pass
