from . import windowing, messages
from .render import WHITE, BLACK

from collections import namedtuple

import pygame
import sys
import os

PADDLE_HEIGHT = 100
PADDLE_WIDTH = 30
HALF_PADDLE_HEIGHT = PADDLE_HEIGHT // 2
PADDLE_X = 50

def mk_game_process(
        position=None,
        size=(300, 300),
        centered=False,
        pinned=True
):
    """
    XXX
    The subprocesses here are basically dumb terminals, only able to draw and
    report their position (and pin themselves). It would be possible to do this
    in a single-process environment, but there are no Python SDL wrappers (or
    other simplistic graphics libs) that support multiple windows as far as I
    can see, and I don't feel like manually dinking with Gtk or worse, X.

    Also, I was explicitly requested to use multiprocessing anyway, so my hands
    would be tied either way.
    """

    def game_process(conn):
        if centered:
            os.environ['SDL_VIDEO_CENTERED'] = '1'

        pygame.init()
        screen = pygame.display.set_mode(size)
        last_renderables = None
        win_handle = pygame.display.get_wm_info()['window']
        if position is not None:
            windowing.set_translation(win_handle, position)
        win_info = windowing.get_win_info(win_handle)
        pin = None

        while True:
            win_handle = pygame.display.get_wm_info()['window']
            win_info = windowing.get_win_info(win_handle)

            in_msgs = conn.recv()

            for in_msg in in_msgs:
                # TODO: Using the same "quit" signaller for clients and terminals
                #       probably a little weak, we should probably have seperate
                #       ClientMessage and ServerMessage namedtuples
                if messages.is_quit(in_msg):
                    # Explicitly _not_ using pygame.quit, since that causes
                    # graphics exceptions and the entire purpose of doing this is
                    # to allow graceful exiting.
                    sys.exit()
                elif messages.is_render(in_msg):
                    if in_msg.info != last_renderables:
                        screen.fill(BLACK)

                        for renderable in in_msg.info:
                            renderable.render(screen, (win_info.x, win_info.y))

                        # TODO: Return bounding boxes out of `render`, convert for
                        #       to map, pass it to this.
                        pygame.display.update()
                elif messages.is_freeze(in_msg):
                    pin = win_info.x, win_info.y
                elif messages.is_unfreeze(in_msg):
                    pin = None
                else:
                    raise NotImplementedError()

            # Pretend that we're still at the pin position if we're supposed to
            # be pinned (i.e. make `winf` track the _logical_ position of the
            # window, ignoring the _actual_ position, which can fluctuate)
            if pin is None:
                winf = win_info
            else:
                windowing.set_translation(win_handle, pin)

                winf = windowing.WindowInfo(
                    x=pin[0],
                    y=pin[1],
                    width=win_info.width,
                    height=win_info.height,
                )

            if any(pygame.event.get(pygame.QUIT)):
                conn.send(messages.quit())
                sys.exit()
            else:
                conn.send(messages.client_state(winf))

    return game_process
