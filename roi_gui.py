import sys
from PyQt5 import QtWidgets
from ui import ui_roi

import numpy as np
from core.widgets.imgTools import find_outlier_pixels, find_brightest_pixels, rm_outlier_pixels
try:
    from core.HXN_databroker import save_data
except ImportError as ex:
    print('[!] Unable to import core.HXN_databroker packages some features will '
          'be unavailable')
    print('[!] (import error: {})'.format(ex))

BADPIX_BRIGHTEST = 0
BADPIX_OUTLIERS = 1
######


class RoiWindow(QtWidgets.QMainWindow, ui_roi.Ui_MainWindow):

    def __init__(self, parent=None, image=None, param=None, main_window=None):
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
        self.reset = self.canvas.reset

        # connect
        self.btn_badpixels_brightest.clicked.connect(lambda: self.find_badpixels(BADPIX_BRIGHTEST))
        self.btn_badpixels_outliers.clicked.connect(lambda : self.find_badpixels(BADPIX_OUTLIERS))
        self.btn_badpixels_correct.clicked.connect(self.correct_badpixels)
        self.ck_show_badpixels.clicked.connect(self.show_badpixels)
        self.btn_save_to_h5.clicked.connect(self.save_to_h5)

        # badpixels
        # : to compute indices w.r.t original image
        # rows = badpixels[0] + offset_y
        # cols = badpixels[1] + offset_x
        self.badpixels_method = BADPIX_BRIGHTEST # method applied to get the badpixels
        self.badpixels = None # indice w.r.t roi
        self.offset_x = None  # offset x to convert indice w.r.t frame (original image)
        self.offset_y = None  # offset y to convert indice w.r.t frame (original image)

        # for h5 operation
        self.main_window = main_window # need to know the caller
        self.roi_width = None
        self.roi_height = None
        self.cx = None
        self.cy = None
        self.sp_threshold.setValue(1.0)

    def find_badpixels(self, op_name):
        img = self.canvas.image
        if img is None:
            return

        if op_name == BADPIX_BRIGHTEST:
            self.btn_badpixels_brightest.setChecked(True)
            self.btn_badpixels_outliers.setChecked(False)
        else:
            self.btn_badpixels_brightest.setChecked(False)
            self.btn_badpixels_outliers.setChecked(True)
        self.badpixels_method = op_name

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
            self.roi_width = roi_width
            self.roi_height = roi_height

            x0 = np.maximum(np.int(np.round(xy[0])), 0)
            y0 = np.maximum(np.int(np.round(xy[1])), 0)
            x1 = np.minimum(x0 + roi_width, width)
            y1 = np.minimum(y0 + roi_height, height)
            # TEST: ROI center
            self.cx = x0 + roi_width//2
            self.cy = y0 + roi_height//2

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
        self.btn_badpixels_correct.setEnabled(True)

    def correct_badpixels(self):
        if self.badpixels is None: return

        img = self.canvas.image
        img = rm_outlier_pixels(img,
                                self.badpixels[0] + self.offset_y,
                                self.badpixels[1] + self.offset_x,
                                self.badpixels_method==BADPIX_BRIGHTEST)

        self.canvas.draw_image(img)
        # update badpixels with corrected one????????
        self.find_badpixels(self.badpixels_method)

    def show_badpixels(self, state):
        self.canvas.show_overlay(state)

    def save_to_h5(self):
        master = self.main_window
        if master is None:
            return

        # need an up-to-date param
        master.update_param_from_gui()
        p = master.param
        if p.z_m == 0.:
            print("[ERROR] detector distance (z_m) is 0 --- maybe forget to set it?", file=sys.stderr)
            return
    
        # get threshold
        threshold = self.sp_threshold.value()

        # get bad pixels
        # TODO: need a better foolproof way 
        if self.badpixels is None or self.offset_x is None or self.offset_y is None:
            self.find_badpixels(BADPIX_OUTLIERS) 
        # TODO: separate this part to another function?
        if len(self.badpixels) == 2 and len(self.badpixels[0]) == len(self.badpixels[1]) > 0:
            badpixels = [self.badpixels[0] + self.offset_y, self.badpixels[1] + self.offset_x]
            print("bad pixels:")
            for x, y in zip(badpixels[0], badpixels[1]):
                print("  (x, y) = ({0}, {1})".format(x, y))
        else:
            badpixels = None
            print("no bad pixels")

        #TODO: ask a QThread to do the work
        #print("center: {0} {1} ".format(self.cx, self.cy), file=sys.stderr)
        save_data(master.db, p, int(p.scan_num), self.roi_width, self.roi_height, cx=self.cx, cy=self.cy,
                  threshold=threshold, bad_pixels=badpixels)
        print("h5 saved.")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = RoiWindow()
    w.show()

    sys.exit(app.exec_())
