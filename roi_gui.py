import sys
from PyQt5 import QtWidgets
from ui import ui_roi

import numpy as np
from core.widgets.imgTools import find_outlier_pixels, find_brightest_pixels

BADPIX_BRIGHTEST = 0
BADPIX_OUTLIERS = 1

class RoiWindow(QtWidgets.QMainWindow, ui_roi.Ui_MainWindow):

    def __init__(self, parent=None, image=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        from core.widgets.mplcanvas import load_image_pil
        img = load_image_pil('./test.tif')
        self.canvas.draw_image(img)
        if image is not None:
            self.canvas.draw_image(image)

        # signal
        self.roi_changed = self.canvas.roi_changed

        # connect
        self.btn_badpixels_brightest.clicked.connect(lambda: self.find_badpixels(BADPIX_BRIGHTEST))
        self.btn_badpixels_outliers.clicked.connect(lambda : self.find_badpixels(BADPIX_OUTLIERS))
        self.ck_show_badpixels.clicked.connect(self.show_badpixels)

        # badpixels
        # : to compute indices w.r.t original image
        # rows = badpixels[0] + offset_y
        # cols = badpixels[1] + offset_x
        self.badpixels = None # indice w.r.t roi
        self.offset_x = None  # offset x to convert indice w.r.t frame (original image)
        self.offset_y = None  # offset y to convert indice w.r.t frame (original image)

    def find_badpixels(self, op_name):
        img = self.canvas.image
        if img is None:
            return

        height, width = img.shape
        roi = self.canvas.get_curr_roi()
        if roi[0] is None or roi[1] is None or roi[2] is None:
            roi_img = img
            self.offset_x = 0
            self.offset_y = 0
        else:
            xy = roi[0]
            roi_width = np.int(np.round(roi[1]))
            roi_height = np.int(np.round(roi[2]))

            x0 = np.maximum(np.int(np.round(xy[0])), 0)
            y0 = np.maximum(np.int(np.round(xy[1])), 0)
            x1 = np.minimum(x0 + roi_width, width)
            y1 = np.minimum(y0 + roi_height, height)

            roi_img = img[y0:y1, x0:x1]
            self.offset_x = x0
            self.offset_y = y0

        if op_name == BADPIX_BRIGHTEST:
            self.badpixels = find_brightest_pixels(roi_img)
        elif op_name == BADPIX_OUTLIERS:
            self.badpixels = find_outlier_pixels(roi_img)
        else:
            self.badpixels = find_brightest_pixels(roi_img)

        self.canvas.set_overlay(self.badpixels[0] + self.offset_y, self.badpixels[1] + self.offset_x)
        self.ck_show_badpixels.setChecked(True)

    def show_badpixels(self, state):
        self.canvas.show_overlay(state)




if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = RoiWindow()
    w.show()

    sys.exit(app.exec_())