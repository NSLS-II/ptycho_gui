from PyQt4 import  QtCore
from datetime import datetime
from core.dpc_param import Param
#from .ptycho.recon_ptycho_gui import recon_gui
#from mpi4py import MPI
import sys, os
import pickle     # dump param into disk
import subprocess # call mpirun from shell


class DPCReconWorker(QtCore.QThread):
    # update signal
    # arg[0]: current iteration number
    update_signal = QtCore.pyqtSignal(int)
    process = None
    #signals = QtCore.pyqtSignal([bool])

    def __init__(self, param:Param=None, parent=None):
        super().__init__(parent)
        self.param = param

    def recon_api(self, param:Param, update_fcn=None, signals=None):
        # self.param.gpus = [0] # GPU #1, for test purpose
        config_path = os.path.expanduser("~") + "/.ptycho_gui_config"
        with open(config_path, "w") as config:
            config.write("working_directory = "+param.working_directory)

        with open(param.working_directory + '.dpc_param.pkl', 'wb') as output:
            pickle.dump(param, output, pickle.HIGHEST_PROTOCOL)  # dump param into disk and let children read it back
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
                                  stderr=subprocess.STDOUT,
                                  env=dict(os.environ, mpi_warn_on_fork='0')) as run_ptycho:
                self.process = run_ptycho # register the subprocess

                while True:
                    output = run_ptycho.stdout.readline()
                    if output == b'' and run_ptycho.poll() is not None:
                        break

                    if output:
                        output = output.decode('utf-8')
                        print(output)
                        output = output.split()
                        if len(output) > 0 and output[0] == "[INFO]" and update_fcn is not None:
                            update_fcn(int(output[2])+1)

                # get the return value 
                return_value = run_ptycho.poll()
                if return_value != 0:
                    message = "At least one MPI process returned a nonzero value, so the whole job is aborted.\n"
                    message += "If you did not manually terminate it, consult the Traceback above to identify the problem."
                    raise Exception(message)
        except Exception as ex:
            print(ex)
            raise ex
        finally:
            # clean up temp file
            os.remove(param.working_directory + '.dpc_param.pkl')

    def run(self):
        print('DPC thread started')
        try:
            self.recon_api(self.param, self.update_signal.emit) #, self.signals)
        except:
            # whatever happened in the MPI processes will always (!) generate traceback,
            # so do nothing here
            pass
        finally:
            print('finally?')

    def kill(self):
        print('killing the subprocess...')
        self.process.terminate()
        self.process.wait()
