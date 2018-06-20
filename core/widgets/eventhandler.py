import numpy as np
from matplotlib.patches import Rectangle

from PyQt5.QtCore import QObject, pyqtSignal

class EventHandler(QObject):
    roi_changed = pyqtSignal(float, float, float, float, name='roiChanged')

    def __init__(self, parent=None, multi_roi=False):
        super().__init__(parent)

        self.cur_xlim = None
        self.cur_ylim = None
        self.x0 = None
        self.y0 = None
        self.x1 = None
        self.y1 = None

        self.multi = multi_roi
        self.rect_count = 0
        self.rect_selected_key = -1
        self.all_rect = {}
        self.rect = None
        self.rect_x0 = None
        self.rect_y0 = None
        self.rect_x1 = None
        self.rect_y1 = None

    def get_roi(self):
        if self.rect_count:
            rect = self.all_rect[self.rect_selected_key]
            return rect.get_xy(), rect.get_width(), rect.get_height()
        else:
            return None, None, None

    def set_roi(self, ax, xy, width, height):
        if self.rect_selected_key >= 0:
            self.all_rect[self.rect_selected_key].set_edgecolor('red')

        rect = Rectangle(xy, width, height, linewidth=1, edgecolor='red', facecolor='none')
        ax.add_patch(rect)
        self.all_rect[self.rect_count] = rect
        self.rect_selected_key = self.rect_count
        self.rect_count += 1

        ax.figure.canvas.draw()

    def set_curr_roi(self, ax, xy, width, height):
        if self.rect_selected_key >= 0:
            rect = self.all_rect[self.rect_selected_key]
            rect.set_xy(xy)
            rect.set_width(width)
            rect.set_height(height)
        else:
            rect = Rectangle(xy, width, height, linewidth=1, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            self.all_rect[self.rect_count] = rect
            self.rect_selected_key = self.rect_count
            self.rect_count += 1
        ax.figure.canvas.draw()


    def zoom_factory(self, ax, base_scale=1.05):
        def zoom(event):
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

        fig = ax.get_figure()
        id = fig.canvas.mpl_connect('scroll_event', zoom)
        return [id]

    def pan_factory(self, ax):
        def on_press(event):
            if not ax.in_axes(event): return
            if event.button != 1: return
            self.cur_xlim = ax.get_xlim()
            self.cur_ylim = ax.get_ylim()
            self.x0 = event.xdata
            self.y0 = event.ydata

        def on_release(event):
            if event.button != 1: return
            self.cur_xlim = None
            self.cur_ylim = None
            self.x0 = None
            self.y0 = None
            ax.figure.canvas.draw()

        def on_motion(event):
            if not ax.in_axes(event): return
            if event.button != 1: return
            if self.x0 is None or self.y0 is None: return

            dx = event.xdata - self.x0
            dy = event.ydata - self.y0
            self.cur_xlim -= dx
            self.cur_ylim -= dy
            ax.set_xlim(self.cur_xlim)
            ax.set_ylim(self.cur_ylim)
            ax.figure.canvas.draw()

        fig = ax.get_figure()
        id1 = fig.canvas.mpl_connect('button_press_event', on_press)
        id2 = fig.canvas.mpl_connect('button_release_event', on_release)
        id3 = fig.canvas.mpl_connect('motion_notify_event', on_motion)

        return [id1, id2, id3]

    def _find_closest_rect(self, x, y):
        min_key = -1
        min_dist = 9999999.
        for key, rect in self.all_rect.items():
            rect.set_edgecolor('gray')
            xy = rect.get_xy()
            width = rect.get_width()
            height = rect.get_height()

            _x0 = xy[0]
            _y0 = xy[1]
            _x1 = _x0 + width
            _y1 = _y0 + height

            x0, x1 = np.minimum(_x0, _x1), np.maximum(_x0, _x1)
            y0, y1 = np.minimum(_y0, _y1), np.maximum(_y0, _y1)
            if x <= x0 or x >= x1 or y <= y0 or y >= y1: continue

            dist = np.min(np.abs([x0 - x, x1 - x, y0 - y, y1 - y]))
            if dist < min_dist:
                min_key = key
                min_dist = dist

        return min_key

    def _remove_rect(self, key):
        if key not in self.all_rect: return

        self.all_rect[key].remove()
        del self.all_rect[key]

        all_rect = {}
        rect_count = 0
        for _, value in self.all_rect.items():
            all_rect[rect_count] = value
            rect_count += 1

        if rect_count:
            all_rect[rect_count - 1].set_edgecolor('red')

        self.all_rect = all_rect
        self.rect_count = rect_count
        self.rect_selected_key = rect_count - 1

    def roi_factory(self, ax):
        def on_press(event):
            if not ax.in_axes(event): return
            if event.button == 1:
                self.rect_x0 = event.xdata
                self.rect_y0 = event.ydata
                if not self.multi: self._remove_rect(0)
            elif event.button == 3:
                x, y = event.xdata, event.ydata
                key = self._find_closest_rect(x, y)
                self._remove_rect(key)
                self.roi_changed.emit(0., 0., 0., 0.)
                ax.figure.canvas.draw()

        def on_release(event):
            if event.button !=1: return
            if self.rect is None: return
            self.all_rect[self.rect_count] = self.rect
            self.rect_selected_key = self.rect_count
            self.rect_count += 1
            self.rect = None

        def on_motion(event):
            if not ax.in_axes(event): return
            if event.button != 1: return
            if self.rect_x0 is None or self.rect_y0 is None: return

            self.rect_x1 = event.xdata
            self.rect_y1 = event.ydata
            width = self.rect_x1 - self.rect_x0
            height = self.rect_y1 - self.rect_y0
            xy = self.rect_x0, self.rect_y0

            if self.rect is None:
                self.rect = Rectangle(xy, width, height, linewidth=1, facecolor='none', edgecolor='red')
                ax.add_patch(self.rect)
            else:
                self.rect.set_width(width)
                self.rect.set_height(height)
                self.rect.set_xy(xy)

            self.roi_changed.emit(xy[0], xy[1], width, height)

            for key, value in self.all_rect.items():
                value.set_edgecolor('gray')

            ax.figure.canvas.draw()

        fig = ax.get_figure()
        id1 = fig.canvas.mpl_connect('button_press_event', on_press)
        id2 = fig.canvas.mpl_connect('button_release_event', on_release)
        id3 = fig.canvas.mpl_connect('motion_notify_event', on_motion)

        return [id1, id2, id3]

    def monitor_factory(self, ax, image_handler):

        def _find_closest_rect(x, y):
            min_key = -1
            min_dist = 9999999.
            for key, rect in self.all_rect.items():
                rect.set_edgecolor('gray')
                xy = rect.get_xy()
                width = rect.get_width()
                height = rect.get_height()

                _x0 = xy[0]
                _y0 = xy[1]
                _x1 = _x0 + width
                _y1 = _y0 + height

                x0, x1 = np.minimum(_x0, _x1), np.maximum(_x0, _x1)
                y0, y1 = np.minimum(_y0, _y1), np.maximum(_y0, _y1)
                if x <= x0 or x >= x1 or y <= y0 or y >= y1: continue

                dist = np.min(np.abs([x0 - x, x1 - x, y0 - y, y1 - y]))
                if dist < min_dist:
                    min_key = key
                    min_dist = dist

            return min_key

        def on_press(event):
            if not ax.in_axes(event): return

            x = event.xdata
            y = event.ydata
            self.x0 = x
            self.y0 = y
            if self.rect_count:
                selected_key = _find_closest_rect(x, y)
                if event.button == 1:
                    if selected_key >= 0:
                        self.all_rect[selected_key].set_edgecolor('red')
                        self.rect_selected_key = selected_key
                    else:
                        self.all_rect[self.rect_count-1].set_edgecolor('red')
                        self.rect_selected_key = self.rect_count-1
                    x1, y1 = self.all_rect[self.rect_selected_key].get_xy()
                    self.x1 = x1
                    self.y1 = y1
                elif event.button == 3 and selected_key >= 0:
                    self.all_rect[selected_key].remove()
                    del self.all_rect[selected_key]
                    all_rect = {}
                    rect_count = 0
                    for _, value in self.all_rect.items():
                        all_rect[rect_count] = value
                        rect_count += 1

                    if rect_count:
                        all_rect[rect_count-1].set_edgecolor('red')

                    self.all_rect = all_rect
                    self.rect_count = rect_count
                    self.rect_selected_key = rect_count-1

                ax.figure.canvas.draw()

        def on_release(event):
            self.x0 = None
            self.y0 = None
            self.x1 = None
            self.y1 = None
            self.rect = None

        def on_motion(event):
            if not ax.in_axes(event): return
            if event.button != 1: return

            x, y = event.xdata, event.ydata
            #value = image_handler.get_cursor_data(event)

            dx = x - self.x0
            dy = y - self.y0
            if self.rect_selected_key >= 0:
                xy = self.x1 + dx, self.y1 + dy
                self.all_rect[self.rect_selected_key].set_xy(xy)

                ax.figure.canvas.draw()

        fig = ax.get_figure()
        id1 = fig.canvas.mpl_connect('button_press_event', on_press)
        id2 = fig.canvas.mpl_connect('motion_notify_event', on_motion)
        id3 = fig.canvas.mpl_connect('button_release_event', on_release)
        return [id1, id2, id3]