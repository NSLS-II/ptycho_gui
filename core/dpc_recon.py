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
        with open('.dpc_param.pkl', 'wb') as output:
            pickle.dump(param, output, pickle.HIGHEST_PROTOCOL)  # dump param into disk and let children read it back
            print("pickle dumped")

        # working version
        mpirun_command = ["mpirun", "-n", str(len(param.gpus)), "python", "./core/ptycho/recon_ptycho_gui.py"]
        with subprocess.Popen(mpirun_command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              env=dict(os.environ, mpi_warn_on_fork='0')) as run_ptycho:
            self.process = run_ptycho # register the subprocess

            while True:
                output = run_ptycho.stdout.readline()
                if output == b'' and run_ptycho.poll() is not None:
                    break

                #if signals is not None and signals[0]:
                #    print("break signal received, exiting...")
                #    with open("test_file", "w") as ttt:
                #       ttt.write("yes")
                #    break

                if output:
                    output = output.decode('utf-8')
                    print(output)
                    output = output.split()
                    if output[0] == "[INFO]" and update_fcn is not None:
                        update_fcn(int(output[2])+1)

            # does GUI wanna know the return value = run_ptycho.poll()?

        # clean up temp file
        os.remove('.dpc_param.pkl')

    def run(self):
        print('DPC thread started')
        try:
            self.recon_api(self.param, self.update_signal.emit) #, self.signals)
        finally:
            print('finally?')

    def kill(self):
        print('killing the subprocess...')
        self.process.terminate()
        self.process.wait()
