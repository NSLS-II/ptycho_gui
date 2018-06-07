import sys
from PyQt5 import QtWidgets

from ui import ui_reconstep

class ReconStepWindow(QtWidgets.QMainWindow, ui_reconstep.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        # connect
        self.slider_iters.valueChanged.connect(self.slider_iters_op)
        self.sb_iter.valueChanged.connect(self.sb_iter_op)
        self.cb_image_kind.currentIndexChanged.connect(self.cb_image_kind_op)
        self.btn_close.clicked.connect(self.btn_close_op)

        self.image_buffer = {}
        self.metric_buffer = {}
        self.current_max_iters = 1
        self.current_iter = 1
        self.current_image_kind_idx = 0

        self.progressBar.setValue(0)

    def is_live_update(self):
        return self.cb_live.isChecked()

    def slider_iters_op(self, it):
        self.sb_iter.setValue(it)
        self.update_images(it)

    def sb_iter_op(self, it):
        self.slider_iters.setValue(it)
        self.update_images(it)

    def cb_image_kind_op(self, idx):
        self.current_image_kind_idx = idx
        self.update_images(self.current_iter)

    def btn_close_op(self):
        self.close()

    def reset_iter(self, max_iters):
        """Called from outside"""
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(max_iters)

        # one-based index
        self.current_max_iters = 1
        self.slider_iters.setValue(1)
        self.slider_iters.setMaximum(1)
        self.sb_iter.setValue(1)
        self.sb_iter.setMaximum(1)

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
                self.current_iter = it

    def update_images(self, it, images=None):
        if images is not None:
            self.image_buffer[it] = [img.copy() for img in images]

        if self.is_live_update() and images is not None:
            selected_image = images[self.current_image_kind_idx].copy()
            self.canvas_image.update_image(selected_image)

        elif it in self.image_buffer:
            selected_image = self.image_buffer[it]
            self.canvas_image.update_image(selected_image[self.current_image_kind_idx])

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    w = ReconStepWindow()
    w.show()

    sys.exit(app.exec_())
