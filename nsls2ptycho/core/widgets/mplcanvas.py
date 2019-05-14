import os
from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.pyplot import Axes
import matplotlib.cm as cm
from mpl_toolkits.axes_grid1.axes_divider import make_axes_area_auto_adjustable

import csv
import numpy as np
from PIL import Image

from nsls2ptycho.core.ptycho.utils import split


def load_image_pil(path):
    """
    Read images using the PIL lib
    """
    file = Image.open(str(path))  # 'I;16B'
    return np.array(file.getdata()).reshape(file.size[::-1])

def load_image_ascii(path):
    """
    Read ASCII images using the csv lib
    """
    delimiter = '\t'
    data = []
    for row in csv.reader(open(path), delimiter=delimiter):
        data.append(row[:-1])
    img = np.array(data).astype(np.double)
    return img

def brush_to_color_tuple(brush):
    r, g, b, a = brush.color().getRgbF()
    return r, g, b

class MplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)

        ax = Axes(fig, [0., 0., 1., 1.])
        fig.add_axes(ax)
        self.axes = ax
        self.fig = fig

        self.canvas = FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        #self.figure.subplots_adjust(left= 0.15, bottom=0.15)
        window_brush = self.window().palette().window()
        fig.set_facecolor(brush_to_color_tuple(window_brush))
        fig.set_facecolor(brush_to_color_tuple(window_brush))

        self.reset()

    def reset(self):
        self.image_handlers = None
        self.line_handlers = []
        self.axes.clear()
        self.axes.set_axis_off() # must be after clear()
        self.draw() # test 

    def compute_initial_figure(self):
        pass

    def axis_on(self):
        self.axes.set_axis_on()
        make_axes_area_auto_adjustable(self.axes)

    def update_image(self, image):
        if self.image_handlers is None:
            self.image_handlers = self.axes.imshow(image)
        else:
            self.image_handlers.set_data(image)
            # amplitude and phase have dramatically different ranges, so rescaling is necessary
            self.image_handlers.autoscale()
        self.draw()

    def update_plot(self, xValues, yValues):

        num_plots = yValues.shape[1]
        if len(self.line_handlers) == 0:
            for i in range(num_plots):
                h = self.axes.plot(xValues, yValues[:,i])
                self.line_handlers.append(h[0])
        else:
            for hidx, h in enumerate(self.line_handlers):
                h.set_data(xValues, yValues[:,hidx])
            self.axes.tick_params(axis='both', labelsize=8)
            self.axes.relim(visible_only=True)
            #self.axes.autoscale(tight=True)
            #self.axes.autoscale_view(tight=True)
            self.axes.autoscale_view()

        self.draw()

    def update_scatter(self, pts, mpi_size, colormap=cm.jet):
        '''
        Plot N scanning points in mpi_size different colors

        Parameters:
            - pts: np.array([[x0, x1, ..., xN], [y0, y1, ..., yN]])
            - mpi_size: number of MPI processes
            - colormap 
        '''
        if len(self.line_handlers) == 0:
            a = split(pts.shape[1], mpi_size)
            colors = colormap(np.linspace(0, 1, len(a)))
            for i in range(mpi_size):
                h = self.axes.scatter(pts[0, a[i][0]:a[i][1]], pts[1, a[i][0]:a[i][1]], c=colors[i])
                self.line_handlers.append(h)
        else: # assuming mpi_size is unchanged
            a = split(pts.shape[1], mpi_size)
            for i, h in enumerate(self.line_handlers):
                h.set_offsets(np.array([pts[0, a[i][0]:a[i][1]], pts[1, a[i][0]:a[i][1]]]).transpose())
            # TODO: handle plot limits?
            ##self.axes.tick_params(axis='both', labelsize=8)
            #self.axes.relim(visible_only=True)
            ##self.axes.autoscale(tight=True)
            ##self.axes.autoscale_view(tight=True)
            #self.axes.autoscale_view()

        self.draw()


class MplCanvasTool(QtWidgets.QWidget):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        super().__init__(parent)

        fig = Figure(figsize=(width, height), dpi=dpi)
        ax = Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        self.ax = ax
        self.fig = fig
        self.canvas = FigureCanvas(fig)
        self.toolbar = NavigationToolbar(self.canvas, self, False)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)

        self.crop_x0 = None
        self.crop_x1 = None
        self.crop_y0 = None
        self.crop_y1 = None

        self.bad_flag = False

    def _on_press(self, event):
        if event.inaxes:
            self.crop_x0 = event.xdata
            self.crop_y0 = event.ydata

    def _on_release(self, event):
        self.crop_x1 = event.xdata
        self.crop_y1 = event.ydata
        if event.inaxes:
            if (self.crop_x0, self.crop_y0) == (self.crop_x1, self.crop_y1):
                pass
                # if self.bad_flag:
                #     self.bad_pixels_widget.addItem('%d, %d' %
                #                                    (int(round(self.crop_x1)),
                #                                     int(round(self.crop_y1))))
            elif self.set_roi_enabled:
                pass
                # if self.his_enabled:
                #     roi_crop = self.roi_img_equ[int(round(self.crop_y0)):
                #                                 int(round(self.crop_y1)),
                #                                 int(round(self.crop_x0)):
                #                                 int(round(self.crop_x1))]
                # else:
                #     roi_crop = self.roi_img[int(round(self.crop_y0)):
                #                             int(round(self.crop_y1)),
                #                             int(round(self.crop_x0)):
                #                             int(round(self.crop_x1))]
                # self.crop_ax.imshow(roi_crop,
                #                     interpolation='nearest',
                #                     origin='upper',
                #                     cmap=self._ref_color_map,
                #                     extent=[int(round(self.crop_x0)),
                #                             int(round(self.crop_x1)),
                #                             int(round(self.crop_y0)),
                #                             int(round(self.crop_y1))])
                #
                # tfont = {'size': '22',
                #          'weight': 'semibold'
                #          }
                #
                # msg = ('ROI will be set as (%d, %d) - (%d, %d)' %
                #        (int(round(self.crop_x0)), int(round(self.crop_y0)),
                #         int(round(self.crop_x1)), int(round(self.crop_y1))))
                # self.crop_ax.set_title(msg,
                #                        **tfont)
                # self.crop_canvas.draw()
                # self.crop_widget.show()

    def _on_motion(self, event):
        pass
        # if self.set_roi_enabled and event.button == 1 and event.inaxes:
        #     self.rect.set_width(event.xdata - self.crop_x0)
        #     self.rect.set_height(event.ydata - self.crop_y0)
        #     self.rect.set_xy((self.crop_x0, self.crop_y0))
        #     self.ax.figure.canvas.draw()




    def update_image(self, image):
        self.ax.cla()
        self.ax.set_axis_off()
        self.ax.imshow(image)
        self.canvas.draw()



# import matplotlib.pyplot as plt
# img = load_image_pil('../../test.tif')
# plt.imshow(img)
# plt.show()













