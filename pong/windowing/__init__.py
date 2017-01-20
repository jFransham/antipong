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
#       (sorry, Wayland). Handles aren't passed between processes so it doesn't
#       matter if the subprocesses are run on different OSes or windowing
#       systems (not that that would happen anyway).

if is_windows():
    from .windows import get_win_info, set_translation
else:
    from .linux import get_win_info, set_translation
