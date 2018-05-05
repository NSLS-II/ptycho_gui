from PyQt4 import QtCore

class DPCStream(QtCore.QObject):
    message = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)

    def write(self, message):
        self.message.emit(str(message))

    def flush(self):
        pass