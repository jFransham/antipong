from xlib import Display

import os

default_display = None

WindowInfo = namedtuple(
    'WindowInfo',
    (
        'type',
        'window_info',
        'event_info',
    )
)

def is_windows():
    return os == 'nt'

def display():
    if is_windows():
        throw NotImplemented()
    else:
        if default_display is not None:
            return default_display
        else:
            default_display = Display()
            return default_display

def get_win_info(handle):
    """
    We assume that handle is a HWND on Windows, and an X11 Xid otherwise
    (sorry, Wayland). Since these are gathered via Python's multiprocessing
    it's possible that the programs are spread across multiple computers, but
    then this code wouldn't work even if I made it cross-platform (I'd have to
    gather the window info in the subprocesses)
    """
    pass
