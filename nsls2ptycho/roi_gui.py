import sys
from PyQt5 import QtWidgets
from nsls2ptycho.ui import ui_roi

import numpy as np
from nsls2ptycho.core.widgets.imgTools import find_outlier_pixels, find_brightest_pixels, rm_outlier_pixels
from nsls2ptycho.core.ptycho_recon import HardWorker
from nsls2ptycho.core.widgets.badpixel_dialog import BadPixelDialog


try:
    from nsls2ptycho.core.HXN_databroker import save_data
except ImportError as ex:
    print('[!] Unable to import core.HXN_databroker packages some features will '
          'be unavailable')
    print('[!] (import error: {})'.format(ex))


class RoiWindow(QtWidgets.QMainWindow, ui_roi.Ui_MainWindow):

    def __init__(self, parent=None, image=None, param=None, main_window=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        #image = np.load('./34784_frame0.npy')
        if image is not None:
            self.canvas.draw_image(image, cmap='gray', init_roi=True, use_log=False)

        # signal
        self.roi_changed = self.canvas.roi_changed
        #self.reset = self.canvas.reset

        # connect
        self.btn_badpixels_outliers.clicked.connect(self.find_badpixels)
        self.btn_badpixels_correct.clicked.connect(self.correct_badpixels)
        self.ck_show_badpixels.clicked.connect(self.show_badpixels)
        self.btn_save_to_h5.clicked.connect(self.save_to_h5)
        self.ck_logscale.clicked.connect(self.use_logscale)
        self.actionBadpixels.triggered.connect(self.open_badpixel_dialog)

        # badpixels
        self.badpixel_dialog = None
        #self.badpixels_method = BADPIX_OUTLIERS # method applied to get the badpixels

        # for h5 operation
        self.main_window = main_window # need to know the caller
        self.roi_width = None
        self.roi_height = None
        self.cx = None
        self.cy = None
        self.sp_threshold.setValue(1.0)
        self._worker_thread = None

    def reset_window(self, image=None, main_window=None):
        '''
        called from outside 
        '''
        self.canvas.reset()
        # TODO: reset bad pixels stored in canvas
        if image is not None:
            self.canvas.draw_image(image)

        #self.badpixels = None
        #self.offset_x = None
        #self.offset_y = None

        self.main_window = main_window
        self.roi_width = None
        self.roi_height = None
        self.cx = None
        self.cy = None
        self.sp_threshold.setValue(1.0)
        self._worker_thread = None

        #self.btn_badpixels_brightest.setChecked(False)
        self.btn_badpixels_outliers.setChecked(False)
        self.ck_show_badpixels.setChecked(False)
        self.btn_badpixels_correct.setChecked(False)
       
    def open_badpixel_dialog(self):
        badpixels = self.canvas.get_badpixels()
        self.badpixel_dialog = BadPixelDialog(self, badpixels)
        #todo: signal-slot for interactive list view
        self.badpixel_dialog.show()

    def find_badpixels(self):
        # always find badpixels over original image data
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
        #todo: update badpixel_dialog if it is opened
        self.ck_show_badpixels.setChecked(True)
        self.btn_badpixels_correct.setEnabled(True)

    def correct_badpixels(self):
        badpixels = self.canvas.get_badpixels()
        if badpixels is None: return

        img = self.canvas.image
        img = rm_outlier_pixels(img, badpixels[0], badpixels[1])

        self.canvas.draw_image(img)
        self.canvas.clear_overlay()
        # update badpixels with corrected one
        self.find_badpixels()

    def show_badpixels(self, state):
        self.canvas.show_overlay(state)

    def use_logscale(self, state):
        self.canvas.use_logscale(state)

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
        # to update roi_width, roi_height, cx, cy
        # if correction is made internally, correct button should be deprecated
        # because after correction bad pixels are updated according to corrected image.
        self.find_badpixels()
        badpixels = self.canvas.get_badpixels()
        # TODO: separate this part to another function?

        if len(badpixels) == 2 and len(badpixels[0]) == len(badpixels[1]) > 0:
            pass
            #print("bad pixels:")
            #for y, x in zip(badpixels[0], badpixels[1]):
            #    print("  (x, y) = ({0}, {1})".format(x, y))
        else:
            badpixels = None
            print("no bad pixels")

        # get blue rois
        blue_rois = self.canvas.get_blue_roi()
        #print(blue_rois)

        thread = self._worker_thread \
               = HardWorker("save_h5", master.db, p, int(p.scan_num), self.roi_width, self.roi_height,
                                       self.cx, self.cy, threshold, badpixels, blue_rois)
        thread.finished.connect(lambda: self.btn_save_to_h5.setEnabled(True))
        thread.exception_handler = master.exception_handler
        self.btn_save_to_h5.setEnabled(False)
        thread.start()

        # update Exp parameters. Note that there's a np.rot90 to the images in save_h5!!!
        master.sp_x_arr_size.setValue(self.roi_height)
        master.sp_y_arr_size.setValue(self.roi_width)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = RoiWindow()
    w.show()

    sys.exit(app.exec_())
