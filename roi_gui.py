import sys
from PyQt5 import QtWidgets
from ui import ui_roi


class RoiWindow(QtWidgets.QMainWindow, ui_roi.Ui_MainWindow):

    def __init__(self, parent=None, image=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        # img = load_image_pil('./test.tif')
        # self.canvas.draw_image(img)
        if image is not None:
            self.canvas.draw_image(image)

        self.roi_changed = self.canvas.roi_changed
        self.reset = self.canvas.reset


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = RoiWindow()
    w.show()

    sys.exit(app.exec_())
