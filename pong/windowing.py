import os
import Xlib

from Xlib.display import Display
from collections import namedtuple

DEFAULT_DISPLAY = None

WindowInfo = namedtuple(
    'WindowInfo',
    (
        'x',
        'y',
        'width',
        'height',
    )
)


def is_windows():
    return os.name == 'nt'


def display():
    global DEFAULT_DISPLAY

    if is_windows():
        raise NotImplementedError()
    else:
        if DEFAULT_DISPLAY is None:
            DEFAULT_DISPLAY = Display()

        return DEFAULT_DISPLAY


def get_win_info(handle):
    """
    We assume that handle is a HWND on Windows, and an X11 Xid otherwise
    (sorry, Wayland). Handles aren't passed between processes so this isn't an
    unfair assumption.
    """

    # TODO: Move all these is_windows calls to the top level (so they're not
    # called every iteration, ugh)
    if is_windows():
        raise NotImplementedError()
    else:
        win = display().create_resource_object('window', handle)
        geometry = win.get_geometry()
        geo = win.query_tree().parent.query_tree().parent.get_geometry()

        x, y = 0, 0

        cur_win = win

        while isinstance(cur_win, Xlib.xobject.drawable.Window):
            cur_geo = cur_win.get_geometry()
            x += cur_geo.x
            y += cur_geo.y

            cur_win = cur_win.query_tree().parent

        return WindowInfo(
            x=x,
            y=y,
            width=geometry.width,
            height=geometry.height,
        )


def set_translation(handle, pos):
    if is_windows():
        raise NotImplementedError()
    else:
        try:
            win = display().create_resource_object('window', handle)

            x, y = pos

            win.query_tree().parent.query_tree().parent.configure(
                x=x,
                y=y,
            )
        except (Xlib.error.BadDrawable, Xlib.error.BadWindow):
            # TODO: If the request fails, do we care? The program will be torn
            #       down anyway.
            pass
