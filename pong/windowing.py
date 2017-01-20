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
        raise NotImplemented()
    else:
        if DEFAULT_DISPLAY is None:
            DEFAULT_DISPLAY = Display()

        return DEFAULT_DISPLAY


def get_win_info(handle):
    """
    We assume that handle is a HWND on Windows, and an X11 Xid otherwise
    (sorry, Wayland). Since these are gathered via Python's multiprocessing
    it's possible that the programs are spread across multiple computers, but
    then this code wouldn't work even if I made it cross-platform (I'd have to
    gather the window info in the subprocesses)
    """

    # TODO: Move all these is_windows calls to the top level (so they're not
    # called every iteration, ugh)
    if is_windows():
        raise NotImplemented()
    else:
        try:
            win = display().create_resource_object('window', handle)

            # HACK: reparenting window managers bone position management
            #       something fierce - what's the "right" way to do this?
            geo = win.query_tree().parent.query_tree().parent.get_geometry()

            return WindowInfo(
                x=geo.x,
                y=geo.y,
                width=geo.width,
                height=geo.height,
            )
        except (Xlib.error.BadDrawable, Xlib.error.BadWindow):
            return None


def set_translation(handle, pos):
    if is_windows():
        raise NotImplemented()
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
