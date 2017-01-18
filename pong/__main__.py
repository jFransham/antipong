"""
Python antipong.
"""

from __future__ import absolute_import

import time
import pygame

from . import messages, windowing, game

from itertools import chain
from multiprocessing import Process, Pipe
from collections import namedtuple

def game_window(fn, *args, **kwargs):
    my_conn, child_conn = Pipe()

    game_fn = game.mk_game_process(fn, *args, **kwargs)

    proc = Process(target=game_fn, args=(child_conn,))
    proc.start()

    return (my_conn, proc)

# TODO: This craps out if I try to open a window in another thread, what
#       happens if I open a window in this thread _first_?
def get_width_height():
    info = pygame.display.Info()
    out = info.current_w, info.current_h
    del info
    return out

def main():
    pad_size = (
        game.PADDLE_WIDTH,
        game.PADDLE_HEIGHT,
    )

    paddle_windows = [
        game_window(
            game.paddle_window(game.PADDLE_X),
            pad_size
        ),
        game_window(
            game.paddle_window(
                1600 - game.PADDLE_X - game.PADDLE_WIDTH
            ),
            pad_size
        ),
    ]

    ball_windows = [
        game_window(game.ball_window),
        game_window(game.ball_window),
        game_window(game.ball_window),
        game_window(game.ball_window),
        game_window(game.ball_window),
    ]

    all_windows = list(chain(ball_windows, paddle_windows))

    # TODO: Yeah.
    window_size = 1600, 900

    slack = 10
    ball_area_rect = (
        game.PADDLE_X + game.PADDLE_WIDTH + slack,
        slack,
        window_size[0] - (game.PADDLE_X + game.PADDLE_WIDTH + slack) * 2,
        window_size[1] - 20 - slack * 2,
    )

    ball_pos = 800, 450
    frame_length = 0.05
    ball_dir = 1, 1
    ball_speed = 100

    while True:
        time.sleep(frame_length)

        ball_pos = (
            ball_pos[0] + ball_speed * frame_length * ball_dir[0],
            ball_pos[1] + ball_speed * frame_length * ball_dir[1],
        )

        if ball_pos[0] < ball_area_rect[0]:
            ball_dir = (1, ball_dir[1])
        elif ball_pos[0] > ball_area_rect[0] + ball_area_rect[2]:
            ball_dir = (-1, ball_dir[1])
        elif ball_pos[1] < ball_area_rect[1]:
            ball_dir = (ball_dir[0], 1)
        elif ball_pos[1] > ball_area_rect[1] + ball_area_rect[3]:
            ball_dir = (ball_dir[0], -1)

        for (g, _) in all_windows:
            g.send(game.GameState(ball_pos, None))

        ball_window_responses = list(
            map(lambda (chan, _): chan.recv(), ball_windows)
        )
        paddle_responses = list(
            map(lambda (chan, _): chan.recv(), paddle_windows)
        )

        msgs = list(chain(ball_window_responses, paddle_responses))

        # Evaluate this first so you don't lose by closing a window containing
        # a ball
        ended = any(map(messages.is_quit, msgs))

        game_is_lost = all(
            map(lambda r: r.info is None, ball_window_responses)
        )

        if not ended and game_is_lost:
            print("You lost :(")
            ended = True

        if ended:
            for (g, _) in all_windows:
                g.send(messages.quit())
           return
        else:
            pass

if __name__ == '__main__':
    main()
