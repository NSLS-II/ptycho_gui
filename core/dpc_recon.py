from PyQt4 import  QtCore
from datetime import datetime
from core.dpc_param import Param

def test_api(param:Param, update_fcn=None):
    for i in range(param.n_iterations):
        print(datetime.now()) # dummy output

        # pass notification to gui
        if update_fcn is not None:
            update_fcn(i+1)

try:
    #from .ptycho.recon_ptycho_gui import recon_gui
    #from mpi4py import MPI
    import sys, os
    import pickle     # test, dump param into disk
    import subprocess # test, call mpirun from shell
    #recon_api = recon_gui
except ImportError as ex:
    print('[!] Unable to import dpc recon packages')
    print('[!] (import error: {})'.format(ex))
    recon_api = test_api


class DPCReconWorker(QtCore.QThread):
    # update signal
    # arg[0]: current iteration number
    update_signal = QtCore.pyqtSignal(int)
    def __init__(self, param:Param=None, parent=None):
        super().__init__(parent)
        self.param = param

    def run(self):
        print('DPC thread started')
        try: 
            self.param.gpus = [0] # GPU #1, for test purpose
            #with open('.dpc_param.pkl', 'wb') as output:
            #   pickle.dump(self.param, output, pickle.HIGHEST_PROTOCOL) # dump param into disk and let children read it back
            #   print("pickle dumped")

            # working version
            mpirun_command = ["mpirun", "-n", str(len(self.param.gpus)), "python", "./core/ptycho/recon_ptycho_gui.py"]
            with subprocess.Popen(mpirun_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, \
                                  env=dict(os.environ, mpi_warn_on_fork='0')) as run_ptycho:
               while True:
                  output = run_ptycho.stdout.readline()
                  if output == b'' and run_ptycho.poll() is not None:
                      break
                  if output:
                      print(output.decode('utf-8'))
               # does GUI wanna know the return value = run_ptycho.poll()?

            # clean up temp file
            os.remove('.dpc_param.pkl')

            ########## test code below... #########
            
            #result = subprocess.run(["mpirun", "-n", str(len(self.param.gpus)), "python", "./core/ptycho/recon_ptycho_gui.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            #print(result)
            #print(result.stdout)
            #print(result.stdout.decode('utf-8')) # attach the stdout to GUI?

            #comm = MPI.COMM_WORLD.Spawn(sys.executable, args = ["./core/ptycho/recon_ptycho_gui.py"], maxprocs = len(self.param.gpus))
            #comm.Disconnect()

            #recon_api(self.param, self.update_signal.emit)
        finally:
            print('finally?')
