import sys
from PyQt5 import QtWidgets
from ui import ui_roi

from core.widgets.mplcanvas import load_image_pil

class RoiWindow(QtWidgets.QMainWindow, ui_roi.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        img = load_image_pil('./test.tif')
        self.canvas.update_image(img)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = RoiWindow()
    w.show()

    sys.exit(app.exec_())