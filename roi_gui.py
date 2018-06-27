import sys
from PyQt5 import QtWidgets
from ui import ui_roi

import numpy as np
from core.widgets.imgTools import find_outlier_pixels, find_brightest_pixels, rm_outlier_pixels
from core.widgets.badpixel_dialog import BadPixelDialog

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

        # from core.widgets.mplcanvas import load_image_pil
        # img = load_image_pil('./test.tif')
        img = np.load('./34784_frame0.npy')
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

        self.actionBadpixels.triggered.connect(self.open_badpixel_dialog)

        # badpixels
        # : to compute indices w.r.t original image
        # rows = badpixels[0] + offset_y
        # cols = badpixels[1] + offset_x
        self.badpixels_method = BADPIX_OUTLIERS # method applied to get the badpixels
        #self.badpixels = None # indice w.r.t roi
        #self.offset_x = None  # offset x to convert indice w.r.t frame (original image)
        #self.offset_y = None  # offset y to convert indice w.r.t frame (original image)

        # for h5 operation
        self.main_window = main_window # need to know the caller
        self.roi_width = None
        self.roi_height = None
        self.cx = None
        self.cy = None
        self.sp_threshold.setValue(1.0)

    def open_badpixel_dialog(self):
        print('open badpixel dialog')
        badpixels = self.canvas.get_badpixels()
        self.badpixel_dialog = BadPixelDialog(self, badpixels)
        self.badpixel_dialog.show()

    def find_badpixels(self, op_name):
        img = self.canvas.image
        if img is None:
            return

        height, width = img.shape
        roi = self.canvas.get_red_roi()
        if roi is None:
            roi_img = img
            x0 = 0
            y0 = 0
            roi_width = width
            roi_height = height
        else:
            x0 = np.clip([roi[0]], 0, width-1)[0]
            y0 = np.clip([roi[1]], 0, height-1)[0]
            roi_width = roi[2]
            roi_height = roi[3]

            region = (
                slice(y0, y0 + roi_height),
                slice(x0, x0 + roi_width)
            )
            roi_img = img[region]

        badpixels = find_outlier_pixels(roi_img)

        self.roi_width = roi_width
        self.roi_height = roi_height
        # TEST: ROI center
        self.cx = x0 + roi_width // 2
        self.cy = y0 + roi_height // 2

        self.canvas.set_overlay(badpixels[0] + y0, badpixels[1] + x0)
        self.ck_show_badpixels.setChecked(True)
        self.btn_badpixels_correct.setEnabled(True)

    def correct_badpixels(self):
        badpixels = self.canvas.get_badpixels()
        if badpixels is None: return

        img = self.canvas.image
        img = rm_outlier_pixels(img,
                                badpixels[0],
                                badpixels[1],
                                self.badpixels_method==BADPIX_BRIGHTEST)

        self.canvas.draw_image(img)
        self.canvas.clear_overlay()
        # update badpixels with corrected one
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
