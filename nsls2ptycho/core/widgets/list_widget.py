from PyQt5 import QtCore, QtGui, QtWidgets
from nsls2ptycho.ui import ui_list_dialog

class ListWidget(QtWidgets.QDialog, ui_list_dialog.Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        self.btn_add_item.clicked.connect(self.add_item)
        self.btn_rm_item.clicked.connect(self.remove_item)
#        self.btn_close.clicked.connect(self.close_dialog)
#
#    def close_dialog(self):
#        self.destroy()

    def add_item(self):
        self.listWidget.addItem(str(self.le_input.text()))
        self.le_input.setText('')
        self.listWidget.sortItems()

    def remove_item(self):
        item = self.listWidget.takeItem(self.listWidget.currentRow())
        self.listWidget.sortItems()
        del item
