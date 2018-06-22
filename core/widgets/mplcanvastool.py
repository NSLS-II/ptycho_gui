import os
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyplot import Axes
import numpy as np

from core.widgets.imgTools import estimate_roi
from core.widgets.eventhandler import EventHandler


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

        # initialized by _get_roi_bar()
        self.sp_x0 = None
        self.sp_y0 = None
        self.sp_w = None
        self.sp_h = None
        self._roi_all = None
        self.ref_roi_side = [64, 96, 128, 160, 192, 224, 256] # x 32, square

        self._actions = {}
        self._active = None
        self._eventHandler = EventHandler()
        self.roi_changed = self._eventHandler.roi_changed
        self._ids = []

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addLayout(self._get_toolbar())
        layout.addLayout(self._get_roi_bar())
        self.setLayout(layout)

        self.image = None
        self.overlay = None
        self.image_handler = None
        self.overlay_handler = None
        self.reset()

    def _get_toolbar(self):
        self.btn_home = QtWidgets.QPushButton('RESET')
        self.btn_pan_zoom = QtWidgets.QPushButton('PAN/ZOOM')
        self.btn_roi = QtWidgets.QPushButton('ROI')
        self.btn_roi_adjust = QtWidgets.QPushButton('ADJUST')

        self.btn_pan_zoom.setCheckable(True)
        self.btn_roi.setCheckable(True)

        self.btn_home.clicked.connect(self._on_reset)
        self.btn_pan_zoom.clicked.connect(lambda: self._update_buttons('pan/zoom'))
        self.btn_roi.clicked.connect(lambda: self._update_buttons('roi'))
        self.btn_roi_adjust.clicked.connect(self._on_adjust_roi)

        self._actions['pan/zoom'] = self.btn_pan_zoom
        self._actions['roi'] = self.btn_roi

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.btn_home)
        layout.addWidget(self.btn_pan_zoom)
        layout.addWidget(self.btn_roi)
        layout.addWidget(self.btn_roi_adjust)
        return layout

    def _get_roi_bar(self):

        self.sp_x0 = QtWidgets.QSpinBox(self)
        self.sp_y0 = QtWidgets.QSpinBox(self)
        self.sp_w = QtWidgets.QSpinBox(self)
        self.sp_h = QtWidgets.QSpinBox(self)
        self._roi_all = [self.sp_x0, self.sp_y0, self.sp_w, self.sp_h]
        for sp in self._roi_all:
            sp.setMaximum(9999.)
            sp.setMinimum(-9999.)
            sp.setValue(0.)
            sp.valueChanged.connect(self._update_roi_canvas)

        self.coord_label = QtWidgets.QLabel('coord labels')

        self._eventHandler.roi_changed.connect(self._update_roi)
        self._eventHandler.coord_changed.connect(self._update_coord)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('x0'))
        layout.addWidget(self.sp_x0)
        layout.addWidget(QtWidgets.QLabel('y0'))
        layout.addWidget(self.sp_y0)
        layout.addWidget(QtWidgets.QLabel('w'))
        layout.addWidget(self.sp_w)
        layout.addWidget(QtWidgets.QLabel('h'))
        layout.addWidget(self.sp_h)
        layout.addWidget(self.coord_label)
        spacerItem = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Preferred)
        layout.addItem(spacerItem)
        return layout

    def _update_coord(self, ix, iy):

        if self.image is None or ix < 0 or ix >= self.image.shape[1] or iy < 0 or iy >= self.image.shape[0]:
            value = 'None'
        else:
            value = '{:.2e}'.format(self.image[iy, ix])

        self.coord_label.setText('({:d}, {:d}), {:s}'.format(ix, iy, value))

    def _update_roi(self, x0, y0, w, h):
        for sp in self._roi_all: sp.valueChanged.disconnect(self._update_roi_canvas)

        self.sp_x0.setValue(x0)
        self.sp_y0.setValue(y0)
        self.sp_w.setValue(w)
        self.sp_h.setValue(h)

        for sp in self._roi_all: sp.valueChanged.connect(self._update_roi_canvas)

    def _update_roi_canvas(self):
        print('_update_roi_canvas')
        x0 = self.sp_x0.value()
        y0 = self.sp_y0.value()
        w = self.sp_w.value()
        h = self.sp_h.value()

        if x0 <= 0 or y0 <= 0 or w <= 0 or h <= 0:
            return

        self._eventHandler.set_curr_roi(self.ax, (x0, y0), w, h)

    def _update_buttons(self, op_name):
        if self._active == op_name:
            self._active = None
        else:
            self._active = op_name

        self._actions['pan/zoom'].setChecked(self._active == 'pan/zoom')
        self._actions['roi'].setChecked(self._active == 'roi')

        for id in self._ids:
            self.canvas.mpl_disconnect(id)
        self._ids = []

        if self._active == 'pan/zoom':
            self._ids = self._eventHandler.zoom_pan_factory(self.ax)
        elif self._active == 'roi':
            roi_ids = self._eventHandler.roi_factory(self.ax)
            self._ids = roi_ids
        else:
            self._ids = self._eventHandler.monitor_factory(self.ax)
            pass
            # if self.image_handler:
            #     self._ids = self._eventHandler.monitor_factory(self.ax, self.image_handler)

    def _on_reset(self):
        if self.image_handler:
            width = self.image.shape[1]
            height = self.image.shape[0]
            self.ax.set_xlim(0, width)
            self.ax.set_ylim(height, 0)
            self.canvas.draw()

    def _on_adjust_roi(self):
        if self.image is None:
            return

        x0 = self.sp_x0.value()
        y0 = self.sp_y0.value()
        w = self.sp_w.value()
        h = self.sp_h.value()

        if w <= 0: w = self.image.shape[1]
        if h <= 0: h = self.image.shape[0]

        cropped_image = self.image[y0:(y0+h), x0:(x0+w)]
        _x0, _y0, _w, _h = estimate_roi(cropped_image)
        cx = np.int(np.round(x0 + _x0 + _w//2))
        cy = np.int(np.round(y0 + _y0 + _h//2))

        print(_x0, _y0, _w, _h)
        x0 = _x0
        y0 = _y0
        w = _w
        h = _h

        # # maybe need to filter ref_roi_side so that all values are less than the image side??
        # def _adjust_side(side):
        #     idx = np.int(np.argmin(np.abs(np.array(self.ref_roi_side) - side)))
        #     return self.ref_roi_side[idx]
        # w = np.minimum(_adjust_side(_w), self.image.shape[1]-1)
        # h = np.minimum(_adjust_side(_h), self.image.shape[0]-1)
        # print(w, h)
        #
        # x0 = np.int(np.maximum(cx - w//2, 0))
        # y0 = np.int(np.maximum(cy - h//2, 0))
        # x1 = x0 + w
        # y1 = y0 + h
        #
        # offset_x = np.maximum(x1 - self.image.shape[1], 0)
        # x0 = np.maximum(x0 - offset_x, 0)
        # x1 = x1 - offset_x
        #
        # offset_y = np.maximum(y1 - self.image.shape[0], 0)
        # y0 = np.maximum(y0 - offset_y, 0)
        # y1 = y1 - offset_y
        #
        # h = y1 - y0
        # w = x1 - x0
        #
        # print(x0, y0, w, h)

        self._eventHandler.set_curr_roi(self.ax, (x0, y0), w, h)
        self._update_roi(x0, y0, w, h)

    def reset(self):
        self.image_handler = None
        self.image = None
        self.overlay = None
        self.overlay_handler = None
        self.ax.clear()
        self.ax.set_axis_off()
        self.canvas.draw()

    def draw_image(self, image, cmap='gray', vmin=None, vmax=None, init_roi=True):
        if self.image_handler is None:
            if vmin is None: vmin = np.min(image)
            if vmax is None: vmax = np.max(image)
            self.image_handler = self.ax.imshow(image, cmap=cmap, vmin=vmin, vmax=vmax)
        else:
            if vmin is None: vmin = np.min(image)
            if vmax is None: vmax = np.max(image)
            self.image_handler.set_data(image)
        self.image = image

        # if init_roi:
        #     self._on_adjust_roi()

        if len(self._ids) == 0:
            self._ids = self._eventHandler.monitor_factory(self.ax)

        self.canvas.draw()

    def set_overlay(self, rows, cols, highlight=(1,0,0,.5)):
        if self.image is None: return
        if len(rows) != len(cols): return

        self.overlay = np.zeros(self.image.shape + (4,), dtype=np.float32)
        self.overlay[rows, cols] = highlight
        if self.overlay_handler is None:
            self.overlay_handler = self.ax.imshow(self.overlay)
        else:
            self.overlay_handler.set_data(self.overlay)
            self.overlay_handler.set_visible(True)
        self.canvas.draw()

    def show_overlay(self, state):
        if self.overlay_handler is None: return
        self.overlay_handler.set_visible(state)
        self.canvas.draw()

    def get_curr_roi(self):
        return self._eventHandler.get_roi()

    def set_roi(self, xy, width, height):
        self._eventHandler.set_roi(self.ax, xy, width, height)

    def set_curr_roi(self, xy, width, height):
        self._eventHandler.set_curr_roi(self.ax, xy, width, height)
