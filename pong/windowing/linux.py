import Xlib

from Xlib.display import Display

from . import WindowInfo

DEFAULT_DISPLAY = None


def display():
    global DEFAULT_DISPLAY

    if DEFAULT_DISPLAY is None:
        DEFAULT_DISPLAY = Display()

    return DEFAULT_DISPLAY


def get_win_info(handle):
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
    win = display().create_resource_object('window', handle)

    x, y = pos

    win.query_tree().parent.query_tree().parent.configure(
        x=x,
        y=y,
    )
