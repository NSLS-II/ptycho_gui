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


class DPCReconWorker(QtCore.QThread):
    # update signal
    # arg[0]: current iteration number
    update_signal = QtCore.pyqtSignal(int)
    process = None

    def __init__(self, param:Param=None, parent=None):
        super().__init__(parent)
        self.param = param

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
        mpirun_command = ["mpirun", "-n", num_processes, "python", "./core/ptycho/recon_ptycho_gui.py"]

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
                            update_fcn(int(stdout[2])+1)

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
