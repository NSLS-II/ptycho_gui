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
    import dpc_recon # import recon code
    #recon_api = your function
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
            recon_api(self.param, self.update_signal.emit)
        finally:
            print('finally?')