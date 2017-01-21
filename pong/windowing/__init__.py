import os

from collections import namedtuple

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

# NOTE: We assume that handle is a HWND on Windows, and an X11 Xid otherwise
#       (sorry, Wayland). This means that this code will probably not work on
#       macOS, although I haven't tried it.
if is_windows():
    from .windows import get_win_info, set_translation
else:
    from .linux import get_win_info, set_translation
