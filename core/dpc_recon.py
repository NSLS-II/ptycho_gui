#from PyQt4 import  QtCore
from PyQt5 import QtCore
from datetime import datetime
from core.dpc_param import Param
#from .ptycho.recon_ptycho_gui import recon_gui
#from mpi4py import MPI
import sys, os
import pickle     # dump param into disk
import subprocess # call mpirun from shell
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK
import numpy as np


class DPCReconWorker(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(int, object) # (interation number, chi arrays)
    process = None # subprocess 

    def __init__(self, param:Param=None, parent=None):
        super().__init__(parent)
        self.param = param

    def _parse_message(self, tokens):
        def _parser(current, upper_limit, target_list):
            if self.param.mode_flag:
                for j in range(upper_limit):
                    target_list.append(float(tokens[current+2+j]))
            elif self.param.multislice_flag:
                raise NotImplementedError("DPCReconWorker's parser doesn't know how to handle multislice yet.") 
            else:
                target_list.append(float(tokens[current+2]))
    
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
                _parser(i, self.param.prb_mode_num, prb_list)
            if token == 'object_chi':
                _parser(i, self.param.obj_mode_num, obj_list)

        # return a dictionary
        result = {'probe_chi':prb_list, 'object_chi':obj_list}

        return it, result


    def recon_api(self, param:Param, update_fcn=None, signals=None):
        config_path = os.path.expanduser("~") + "/.ptycho_gui_config"
        with open(config_path, "w") as config:
            config.write("working_directory = "+param.working_directory)

        with open(param.working_directory + '.dpc_param.pkl', 'wb') as output:
            # dump param into disk and let children read it back
            pickle.dump(param, output, pickle.HIGHEST_PROTOCOL)
            print("pickle dumped")

        # working version
        if param.gpu_flag:
            num_processes = str(len(param.gpus))
        else:
            num_processes = str(1)
        mpirun_command = ["mpirun", "-n", num_processes, "python", "-W", "ignore", "./core/ptycho/recon_ptycho_gui.py"]

        try:
            return_value = None
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
                        print(stdout)
                        stdout = stdout.split()
                        if len(stdout) > 0 and stdout[0] == "[INFO]" and update_fcn is not None:
                            it, result = self._parse_message(stdout)
                            #print(result['probe_chi'])
                            update_fcn(it+1, result)

                    if stderr:
                        stderr = stderr.decode('utf-8')
                        print(stderr, file=sys.stderr)

                # get the return value 
                return_value = run_ptycho.poll()

            if return_value != 0:
                message = "At least one MPI process returned a nonzero value, so the whole job is aborted.\n"
                message += "If you did not manually terminate it, consult the Traceback above to identify the problem."
                raise Exception(message)
        except Exception as ex:
            print(ex, file=sys.stderr)
            #raise ex
        finally:
            # clean up temp file
            os.remove(param.working_directory + '.dpc_param.pkl')

    def run(self):
        print('DPC thread started')
        try:
            self.recon_api(self.param, self.update_signal.emit)
        # whatever happened in the MPI processes will always (!) generate traceback,
        # so do nothing here
        #except:
        #    pass
        finally:
            print('finally?')

    def kill(self):
        print('killing the subprocess...')
        self.process.terminate()
        self.process.wait()


class DPCReconFakeWorker(QtCore.QThread):
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





