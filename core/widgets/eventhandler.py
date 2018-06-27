import numpy as np
from matplotlib.patches import Rectangle

from PyQt5.QtCore import QObject, pyqtSignal

RED_EDGECOLOR = (1., 0., 0., 1.)
BLUE_EDGECOLOR = (0., 0., 1., 1.)

class EventHandler(QObject):
    ### signals
    # signal for ROI ==> (x0, y0, w, h)
    # x0, y0: xy-coordinate of upper-left corner
    # w, h: width and height of the roi
    roi_changed = pyqtSignal(int, int, int, int, name='roiChanged')

    # signal for coordinate of the mouse pointer ==> (x, y)
    # x, y: xy-coordinate of the mouse pointer on the axis
    coord_changed = pyqtSignal(int, int, name='coordChanged')

    # signal for brushed pixels ==> (x, y)
    brush_changed = pyqtSignal(tuple, name='brushChanged')

    def __init__(self, parent=None):
        super().__init__(parent)

        # variables for panning
        self.pan_cur_xlim = None  # temporal
        self.pan_cur_ylim = None  # temporal
        self.pan_x0 = None        # temporal
        self.pan_y0 = None        # temporal

        # variable for roi
        self.coord_x_ratio = None
        self.coord_y_ratio = None
        self.rect_x0 = None       # temporal
        self.rect_y0 = None       # temporal
        self.rect_x1 = None       # temporal
        self.rect_y1 = None       # temporal
        self.rect_tx = None
        self.rect_ty = None
        self.tmp_rect = None
        self.ref_rect = None      # currently selected roi
        self.ref_idx = -1         # index of currently selected roi
        self.all_rect = []        # list of roi

        # variable for picking pixels (brush by mouse pointer)
        self.pixel_visited = None
        self.on_brush = False


    # coord related -- common actionc for all
    def emit_coord(self, event):
        if event.xdata is None or event.ydata is None: return
        ix = np.int(np.floor(event.xdata + 0.5))
        iy = np.int(np.floor(event.ydata + 0.5))
        self.coord_changed.emit(ix, iy)

    def emit_brush(self, item):
        self.brush_changed.emit(item)

    def emit_roi(self, rect):
        if rect is None:
            self.roi_changed.emit(0, 0, 0, 0)
        else:
            x0, y0 = rect.get_xy()
            width = rect.get_width()
            height = rect.get_height()

            if width < 0:
                x0 = x0 + width
                width = -width

            if height < 0:
                y0 = y0 + height
                height = -height

            x0 = np.int(np.floor(x0 + 0.5))
            y0 = np.int(np.floor(y0 + 0.5))
            width = np.int(np.round(width))
            height = np.int(np.round(height))

            self.roi_changed.emit(x0, y0, width, height)


    #### ROI related ####
    # def get_roi(self):
    #     if self.rect_count:
    #         rect = self.all_rect[self.rect_selected_key]
    #         return rect.get_xy(), rect.get_width(), rect.get_height()
    #     else:
    #         return None, None, None
    def get_red_roi(self):
        roi = []
        for rect in self.all_rect:
            if rect.get_edgecolor() == RED_EDGECOLOR:
               roi.append((
                   rect.get_xy(),
                   rect.get_width(),
                   rect.get_height()
               ))
        return roi

    def get_blue_roi(self):
        roi = []
        for rect in self.all_rect:
            if rect.get_edgecolor() == BLUE_EDGECOLOR:
               roi.append((
                   rect.get_xy(),
                   rect.get_width(),
                   rect.get_height()
               ))
        return roi

    def set_curr_roi(self, ax, xy, width, height):
        if self.ref_rect is None:
            rect = Rectangle(xy, width, height, linewidth=1, linestyle='dashed',
                             edgecolor=RED_EDGECOLOR, facecolor='none')
            ax.add_patch(rect)
            self.all_rect.append(rect)
            self.ref_rect = rect
            self.ref_idx = len(self.all_rect) - 1
        else:
            self.ref_rect.set_xy(xy)
            self.ref_rect.set_width(width)
            self.ref_rect.set_height(height)

        ax.figure.canvas.draw()

    def _find_closest_rect(self, x, y, delta=2.):
        min_dist = 9999999.
        ref_rect = None
        ref_idx = -1
        for idx, rect in enumerate(self.all_rect):
            xy = rect.get_xy()
            width = rect.get_width()
            height = rect.get_height()

            _x0 = xy[0]
            _y0 = xy[1]
            _x1 = _x0 + width
            _y1 = _y0 + height

            # check if the mouse pointer is around edges of this rect
            in_up_bound = _x0 - delta <= x <= _x0 + delta
            in_lo_bound = _x1 - delta <= x <= _x1 + delta
            in_l_bound  = _y0 - delta <= y <= _y0 + delta
            in_r_bound  = _y1 - delta <= y <= _y1 + delta

            if in_up_bound or in_lo_bound or in_l_bound or in_r_bound:
                dist = np.min(np.abs([_x0 - x, _x1 - x, _y0 - y, _y1 - y]))
                if dist < min_dist:
                    min_dist = dist
                    ref_rect = rect
                    ref_idx = idx

        return ref_rect, ref_idx

    #### other helpers ####
    # ...


    # create zoom/pan handler
    def zoom_pan_factory(self, ax, base_scale=1.05):
        def on_scroll(event):
            if not ax.in_axes(event): return

            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()

            x, y = event.xdata, event.ydata
            if event.button == 'down':
                scale_factor = 1. / base_scale
            elif event.button == 'up':
                scale_factor = base_scale
            else:
                scale_factor = 1
                print('[!] Error:zoom: {:s}'.format(event.button))

            x_left = x - cur_xlim[0]
            x_right = cur_xlim[1] - x
            y_top = y - cur_ylim[0]
            y_bottom = cur_ylim[1] - y

            ax.set_xlim([x - x_left*scale_factor, x + x_right*scale_factor])
            ax.set_ylim([y - y_top*scale_factor, y + y_bottom*scale_factor])
            ax.figure.canvas.draw()

        def on_press(event):
            if not ax.in_axes(event): return
            if event.button != 1: return
            self.pan_cur_xlim = ax.get_xlim()
            self.pan_cur_ylim = ax.get_ylim()
            self.pan_x0 = event.xdata
            self.pan_y0 = event.ydata

        def on_release(event):
            self.pan_cur_xlim = None
            self.pan_cur_ylim = None
            self.pan_x0 = None
            self.pan_y0 = None

        def on_motion(event):
            if not ax.in_axes(event): return
            self.emit_coord(event)

            if event.button != 1: return
            if self.pan_cur_xlim is None: return
            if self.pan_cur_ylim is None: return
            if self.pan_x0 is None or self.pan_y0 is None: return

            dx = event.xdata - self.pan_x0
            dy = event.ydata - self.pan_y0
            self.pan_cur_xlim -= dx
            self.pan_cur_ylim -= dy
            ax.set_xlim(self.pan_cur_xlim)
            ax.set_ylim(self.pan_cur_ylim)
            ax.figure.canvas.draw()

        fig = ax.get_figure()
        return [
            fig.canvas.mpl_connect('scroll_event', on_scroll),
            fig.canvas.mpl_connect('button_press_event', on_press),
            fig.canvas.mpl_connect('button_release_event', on_release),
            fig.canvas.mpl_connect('motion_notify_event', on_motion)
        ]

    # create roi handler
    def roi_factory(self, ax):
        def on_press(event):
            if not ax.in_axes(event): return
            self.coord_x_ratio = event.xdata / event.x
            self.coord_y_ratio = (ax.get_ylim()[0] - event.ydata) / event.y

            ref_rect, ref_idx = self._find_closest_rect(event.xdata, event.ydata, delta=2.)
            self.rect_x0 = None
            self.rect_y0 = None

            # left click, init new roi
            if event.button == 1 and ref_rect is None and ref_idx == -1:
                self.rect_x0 = event.xdata
                self.rect_y0 = event.ydata

                # make solid line for all existing roi
                for rect in self.all_rect: rect.set_linestyle('solid')

            # left click, select an existing roi
            elif event.button == 1 and ref_rect is not None and ref_idx >= 0:

                if event.dblclick:
                    clr = RED_EDGECOLOR
                    if self.ref_rect.get_edgecolor() == RED_EDGECOLOR:
                        clr = BLUE_EDGECOLOR
                    self.ref_rect.set_edgecolor(clr)
                else:
                    self.ref_rect = ref_rect
                    self.ref_idx = ref_idx
                    self.rect_tx = event.xdata
                    self.rect_ty = event.ydata

                    # make solid line for all existing roi except the selected one
                    for rect in self.all_rect: rect.set_linestyle('solid')
                    self.ref_rect.set_linestyle('dashed')

            # right click, delete the selected roi
            elif event.button == 3 and ref_rect is not None and ref_idx >=0:
                self.ref_rect = ref_rect
                self.ref_idx = ref_idx

                # make solid line for all existing roi except the selected one
                for rect in self.all_rect: rect.set_linestyle('solid')
                self.ref_rect.set_linestyle('dashed')

        def on_release(event):
            # event end for initializing new roi
            if event.button == 1 and self.tmp_rect is not None:
                self.all_rect.append(self.tmp_rect)
                self.ref_rect = self.tmp_rect
                self.tmp_rect = None
                self.rect_x0 = None
                self.rect_y0 = None

            # event end for selecting a roi
            elif event.button == 1 and self.ref_rect is not None and self.ref_idx >= 0 \
                    and self.rect_x0 is None and self.rect_y0 is None:
                self.rect_tx = None
                self.rect_ty = None
                self.emit_roi(self.ref_rect)

            # event end for deleting a roi
            elif event.button == 3 and self.ref_rect is not None and self.ref_idx >= 0:
                self.ref_rect.remove()
                try:
                    del self.all_rect[self.ref_idx]
                except IndexError as ex:
                    print('[!] ROI index out of range, ignore delete event')
                self.ref_rect = None
                self.ref_idx = -1
                if len(self.all_rect):
                    self.ref_rect = self.all_rect[-1]
                    self.ref_idx = len(self.all_rect) - 1
                    self.ref_rect.set_linestyle('dashed')
                self.emit_roi(self.ref_rect)

            ax.figure.canvas.draw()

        def on_motion(event):
            self.emit_coord(event)

            if event.button == 1:
                if ax.in_axes(event):
                    self.rect_x1 = event.xdata
                    self.rect_y1 = event.ydata
                else:
                    self.rect_x1 = self.coord_x_ratio * event.x
                    self.rect_y1 = ax.get_ylim()[0] - self.coord_y_ratio * event.y

                # on motion event for drawing new roi
                if self.rect_x0 is not None and self.rect_y0 is not None:

                    self.rect_x1 = np.clip(self.rect_x1, ax.get_xlim()[0] + 0.5, ax.get_xlim()[1] - 0.5)
                    self.rect_y1 = np.clip(self.rect_y1, ax.get_ylim()[1] + 0.5, ax.get_ylim()[0] - 0.5)

                    width = self.rect_x1 - self.rect_x0
                    height = self.rect_y1 - self.rect_y0
                    if self.tmp_rect is None:
                        self.tmp_rect = Rectangle((self.rect_x0, self.rect_y0), width, height,
                                                  linewidth=1, linestyle='dashed',
                                                  facecolor='none', edgecolor=RED_EDGECOLOR)
                        ax.add_patch(self.tmp_rect)
                    else:
                        self.tmp_rect.set_width(width)
                        self.tmp_rect.set_height(height)

                    self.emit_roi(self.tmp_rect)
                    ax.figure.canvas.draw()

                # on motion event for moving the selected roi
                elif self.ref_rect is not None and self.ref_idx >=0 and \
                        self.rect_tx is not None and self.rect_ty is not None:

                    dx = self.rect_tx - self.rect_x1
                    dy = self.rect_ty - self.rect_y1

                    x0, y0 = self.ref_rect.get_xy()

                    x0 -= dx
                    y0 -= dy
                    x1 = x0 + self.ref_rect.get_width()
                    y1 = y0 + self.ref_rect.get_height()

                    if ax.get_xlim()[0] + 0.5 <= x0 <= ax.get_xlim()[1] - 0.5 and \
                       ax.get_ylim()[1] + 0.5 <= y0 <= ax.get_ylim()[0] - 0.5 and \
                       ax.get_xlim()[0] + 0.5 <= x1 <= ax.get_xlim()[1] - 0.5 and \
                       ax.get_ylim()[1] + 0.5 <= y1 <= ax.get_ylim()[0] - 0.5:

                        self.ref_rect.set_xy((x0, y0))
                        self.ref_rect.set_width(x1 - x0)
                        self.ref_rect.set_height(y1 - y0)
                        self.emit_roi(self.ref_rect)
                        ax.figure.canvas.draw()

                    self.rect_tx = self.rect_x1
                    self.rect_ty = self.rect_y1

        fig = ax.get_figure()
        id1 = fig.canvas.mpl_connect('button_press_event', on_press)
        id2 = fig.canvas.mpl_connect('button_release_event', on_release)
        id3 = fig.canvas.mpl_connect('motion_notify_event', on_motion)

        return [id1, id2, id3]

    # create monitor handler
    def monitor_factory(self, ax):
        def _make_pixel_item(x, y):
            _x = np.int(np.floor(x + 0.5))
            _y = np.int(np.floor(y + 0.5))
            _str = '{:d},{:d}'.format(_x, _y)
            return _str, (_x, _y)

        def on_press(event):
            if not ax.in_axes(event): return

            if event.button == 1:
                key, item = _make_pixel_item(event.xdata, event.ydata)
                self.emit_brush(item)
                self.on_brush = True
                self.pixel_visited = key

        def on_release(event):
            if event.button == 1 and self.on_brush:
                self.on_brush = False

        def on_motion(event):
            if not ax.in_axes(event): return
            self.emit_coord(event)

            if self.on_brush:
                key, item = _make_pixel_item(event.xdata, event.ydata)
                if key != self.pixel_visited:
                    self.emit_brush(item)
                self.pixel_visited = key



        fig = ax.get_figure()
        id1 = fig.canvas.mpl_connect('button_press_event', on_press)
        id2 = fig.canvas.mpl_connect('motion_notify_event', on_motion)
        id3 = fig.canvas.mpl_connect('button_release_event', on_release)
        return [id1, id2, id3]




