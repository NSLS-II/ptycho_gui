import sys
from PyQt5 import QtWidgets
from ui import ui_reconstep

import numpy as np


class ReconStepWindow(QtWidgets.QMainWindow, ui_reconstep.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        # connect
        self.slider_iters.valueChanged.connect(self.slider_iters_sb_iter_op)
        self.sb_iter.valueChanged.connect(self.slider_iters_sb_iter_op)
        self.cb_image_object.currentIndexChanged.connect(self.cb_image_object_op)
        self.cb_image_probe.currentIndexChanged.connect(self.cb_image_probe_op)
        self.btn_close.clicked.connect(self.btn_close_op)

        # TODO: enable (and rename) these buttons when they are implemented
        self.pushButton.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.pushButton_3.setEnabled(False)
        #self. ...

        self.reset_window()

    def reset_window(self, iterations=50, slider_interval=1):
        """Called from outside"""
        self.image_buffer = {}
        self.metric_buffer_it = []
        self.metric_buffer = []
        self.current_max_iters = 1
        self.progressBar.setValue(0)
        self.reset_iter(iterations, slider_interval)
        # can we reset the figures here???
        self.canvas_object.reset()
        self.canvas_probe.reset()
        self.canvas_object_chi.reset()
        self.canvas_object_chi.axis_on()
        self.canvas_probe_chi.reset()
        self.canvas_probe_chi.axis_on()

    def is_live_update(self):
        return self.ck_live.isChecked()

    def slider_iters_sb_iter_op(self, it):
        # lock the slider position to available values
        temp = (it - self.sb_iter.minimum()) % self.sb_iter.singleStep()
        if temp == 0:
            pass
        elif temp >= self.sb_iter.singleStep() - temp:
            it += self.sb_iter.singleStep() - temp
        else:
            it -= temp
            
        self.slider_iters.setValue(it)
        self.sb_iter.setValue(it)
        self.update_images(it)

    def cb_image_object_op(self, idx):
        it = self.sb_iter.value()
        if it in self.image_buffer:
            images_to_show = self.image_buffer[it]
            object_image = images_to_show[idx]
            self.canvas_object.update_image(object_image)

    def cb_image_probe_op(self, idx):
        it = self.sb_iter.value()
        if it in self.image_buffer:
            images_to_show = self.image_buffer[it]
            probe_image = images_to_show[idx+2]
            self.canvas_probe.update_image(probe_image)

    def btn_close_op(self):
        # todo: close with signal to main window
        self.reset_window()
        self.close()

    def reset_iter(self, max_iters, interval):
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(max_iters)

        # one-based index
        self.current_max_iters = 1
        self.slider_iters.setValue(1)
        self.slider_iters.setMinimum(1)
        self.slider_iters.setMaximum(1)
        self.slider_iters.setSingleStep(interval)
        self.sb_iter.setValue(1)
        self.sb_iter.setMinimum(1)
        self.sb_iter.setMaximum(1)
        self.sb_iter.setSingleStep(interval)

    def update_iter(self, it):
        """Called from outside"""
        self.progressBar.setValue(it)

        if self.current_max_iters < it:
            self.slider_iters.setMaximum(it)
            self.sb_iter.setMaximum(it)
            self.current_max_iters = it

        if self.is_live_update():
            self.slider_iters.setValue(it)
            self.sb_iter.setValue(it)

    def update_images(self, it, images=None):
        if images is not None:
            # just hold the mmap reference, don't do expansive copy
            self.image_buffer[it] = images

        images_to_show = None
        if self.is_live_update() and images is not None:
            images_to_show = images
        elif it in self.image_buffer:
            images_to_show = self.image_buffer[it]

        if images_to_show is not None:
            object_image = images_to_show[self.cb_image_object.currentIndex()]
            probe_image = images_to_show[self.cb_image_probe.currentIndex()+2]
            self.canvas_object.update_image(object_image)
            self.canvas_probe.update_image(probe_image)

    def update_metric(self, it, data):
        self.metric_buffer_it.append(it)
        self.metric_buffer.append(data)

        # get key from combo box
        object_to_plot = np.array([ d['object_chi'] for d in self.metric_buffer])
        probe_to_plot  = np.array([ d['probe_chi'] for d in self.metric_buffer])
        self.canvas_object_chi.update_plot(self.metric_buffer_it, object_to_plot)
        self.canvas_probe_chi.update_plot(self.metric_buffer_it, probe_to_plot)

    def debug(self):
        ''' called from MainWindow'''
        for key in self.image_buffer:
            print("#{}: ".format(key), end='', file=sys.stderr)
            for item in self.image_buffer[key]:
                print("{} ".format(hex(id(item))), end='', file=sys.stderr)
            print("", file=sys.stderr)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = ReconStepWindow()
    w.show()

    sys.exit(app.exec_())
