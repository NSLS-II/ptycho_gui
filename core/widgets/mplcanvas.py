from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

def brush_to_color_tuple(brush):
    r, g, b, a = brush.color().getRgbF()
    return r, g, b

class MplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.compute_initial_figure()

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.figure.subplots_adjust(top=0.95, bottom=0.15)
        window_brush = self.window().palette().window()
        fig.set_facecolor(brush_to_color_tuple(window_brush))
        fig.set_facecolor(brush_to_color_tuple(window_brush))

    def compute_initial_figure(self):
        pass

    def update_image(self, image):
        self.axes.cla()
        self.axes.imshow(image)
        self.draw()