from . import windowing, messages

from collections import namedtuple

import pygame
import sys
import os

PADDLE_HEIGHT = 100
PADDLE_WIDTH = 30
HALF_PADDLE_HEIGHT = PADDLE_HEIGHT // 2

PADDLE_X = 50
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

PINNED = 'pinned'

GameState = namedtuple('GameState', ['ball', 'score'])

def contains(inner, outer):
    p_x, p_y = inner
    x, y, w, h = outer
    return (
        p_x >= x and
        p_x <= x + w and
        p_y >= y and
        p_y <= y + h
    )

def ball_window(game_state, screen, win_info):
    if contains(
        inner=game_state.ball,
        outer=(
            win_info.x,
            win_info.y,
            win_info.width,
            win_info.height,
        ),
    ):
        # This is a pretty inefficient drawing algorithm, but sue me
        screen.fill(BLACK)
        # TODO: Magick numbers
        pygame.draw.circle(
            screen,
            WHITE,
            (
                int(game_state.ball[0] - win_info.x),
                int(game_state.ball[1] - win_info.y),
            ),
            10,
        )
        pygame.display.update()

        return PINNED
    else:
        screen.fill(BLACK)
        pygame.display.update()

        return None

def paddle_window(x):
    def paddle_window_inner(game_state, screen, win_info):
        screen.fill(WHITE)
        pygame.display.update()

        return (
            x,
            game_state.ball[1] - HALF_PADDLE_HEIGHT,
        )

    return paddle_window_inner

def score_window(game_state, screen, win_info):
    return (0, 0)

def mk_game_process(fn, size=(300, 300)):
    """
    XXX
    The subprocesses here are basically dumb terminals, only able to draw and
    report their position (and move). It would be possible to do this in a
    single-process environment, but there are no Python SDL wrappers (or other
    simplistic graphics libs) that support multiple windows as far as I can
    see, and I don't feel like manually dinking with Gtk.

    Also, I was explicitly requested to use multiprocessing anyway, so my hands
    would be tied either way.
    """

    def game_process(conn):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        screen = pygame.display.set_mode(size)
        win_handle = pygame.display.get_wm_info()['window']
        win_info = windowing.get_win_info(win_handle)
        pin = None

        while True:
            win_handle = pygame.display.get_wm_info()['window']
            win_info = windowing.get_win_info(win_handle)

            game_state = conn.recv()

            # HACK: We can probably do this better
            if messages.is_quit(game_state):
                # Explicitly _not_ using pygame.quit, since that causes
                # graphics exceptions and the entire purpose of doing this is
                # to allow graceful exiting.
                sys.exit()

            win_action = fn(game_state, screen, win_info)

            if win_action == PINNED:
                if pin is None:
                    pin = win_info.x, win_info.y
                # TODO: This doesn't work, just ignore it for now and we'll get
                #       back to it
                # windowing.set_translation(win_handle, pin)
            else:
                pin = None

                if win_action is not None:
                    windowing.set_translation(win_handle, win_action)

            if any(pygame.event.get(pygame.QUIT)):
                conn.send(messages.quit())
                sys.exit()
            else:
                conn.send(messages.action(win_action))

    return game_process
