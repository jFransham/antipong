from . import windowing, messages
from .render import BLACK

import pygame
import sys
import os
import time


def shutdown():
    pygame.quit()
    sys.exit()


class GameProcess(object):
    """
    A single instance of the game's client processes

    NOTE: On Linux I can pickle closures, but to get this to run on Windows I
          have to make this single-method class. The documentation says I
          shouldn't be able to pickle closures at all, so I don't know why
          that's kosher on Linux.
    """

    position=None
    size=None
    centered=None
    pinned=None

    def __init__(
        self,
        position=None,
        size=(300, 300),
        centered=False,
        pinned=False
    ):
        self.position = position
        self.size = size
        self.centered = centered
        self.pinned = pinned

    def go(self, conn):
        if self.centered:
            os.environ['SDL_VIDEO_CENTERED'] = '1'

        pygame.init()
        surface = pygame.display.set_mode(self.size)
        win_handle = pygame.display.get_wm_info()['window']

        if self.position is not None:
            windowing.set_translation(win_handle, self.position)

        win_info = windowing.get_win_info(win_handle)

        if self.pinned:
            pin = win_info.x, win_info.y
        else:
            pin = None

        while True:
            win_handle = pygame.display.get_wm_info()['window']
            win_info = windowing.get_win_info(win_handle)

            in_msgs = messages.consume_channel_buffer(conn)

            for in_msg in in_msgs:
                # TODO: Using the same "quit" signaller for clients and
                #       terminals is probably a little weak, maybe we should
                #       have seperate ClientMessage and ServerMessage
                #       namedtuples
                if messages.is_quit(in_msg):
                    shutdown()
                elif messages.is_render(in_msg):
                    # TODO: On the parent, only send renderables that would be
                    #       rendered on the child and then diff it with the
                    #       last frame's renderables, so most frames won't call
                    #       update. Currently not necessary because we've got
                    #       plenty FPS to spare.

                    surface.fill(BLACK)

                    for renderable in in_msg.info:
                        # Explicitly use the actual position, not the logical
                        # position (see below for an explanation of the
                        # difference). With my current WM setup this doesn't
                        # help much, but if you had a window manager that
                        # ignored/buffered messages to set position while the
                        # window is being dragged it would improve the visuals
                        # a fair amount.
                        renderable.render(surface, (win_info.x, win_info.y))

                    # TODO: Return bounding boxes out of `render`, convert
                    #       for to map, pass it to this. Again, not necessary
                    #       because we don't need the performance.
                    pygame.display.update()
                elif messages.is_freeze(in_msg):
                    if not pin and not self.pinned:
                        pin = win_info.x, win_info.y
                elif messages.is_unfreeze(in_msg):
                    if not self.pinned:
                        pin = None
                else:
                    print('Cannot interpret {}'.format(in_msg))
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
                shutdown()
            else:
                conn.send(messages.client_state(winf))


def run_process(game_process, connection):
    """
    Just a wrapper to allow using this with the `Process` API. This function
    will never return.

    :param game_process: An instance of `GameProcess`
    :param connection:   An endpoint of a `Pipe`
    """
    game_process.go(connection)
