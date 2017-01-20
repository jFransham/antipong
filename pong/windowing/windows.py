import ctypes

from . import WindowInfo


class get_wnd_rect(ctypes.Structure):
    _fields_ = [
        ('L', ctypes.c_int),
        ('T', ctypes.c_int),
        ('R', ctypes.c_int),
        ('B', ctypes.c_int),
    ]


def get_win_info(handle):
    out_rect = get_wnd_rect()
    ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(out_rect))

    return WindowInfo(
        x=int(out_rect.L),
        y=int(out_rect.T),
        width=int(out_rect.R - out_rect.L),
        height=int(out_rect.B - out_rect.T),
    )


def set_translation(handle, pos):
    current = get_win_info(handle)

    err = ctypes.windll.user32.MoveWindow(
        handle,
        ctypes.c_int(pos[0]),
        ctypes.c_int(pos[1]),
        ctypes.c_int(current.width),
        ctypes.c_int(current.height),
        ctypes.c_bool(False),
    )

    # Returns 0 on failure
    # https://msdn.microsoft.com/en-us/library/ms633534(VS.85).aspx
    if err == ctypes.c_bool(0):
        raise ctypes.WinError()
