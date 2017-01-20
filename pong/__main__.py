"""
Python antipong.
"""

from __future__ import absolute_import

import time
import pygame

from . import messages, windowing, game, render, physics

from itertools import repeat
from multiprocessing import Process, Pipe
from collections import namedtuple

def game_window(*args, **kwargs):
    my_conn, child_conn = Pipe()

    game_fn = game.mk_game_process(*args, **kwargs)

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
    # TODO: Yeah.
    window_size = 1600, 900
    ball_pos = 800, 450
    frame_length = 0.05
    ball_dir = 1, 1
    ball_speed = 100
    ball_radius = 10
    paddle_height = 100
    paddle_width = 30
    half_paddle_height = paddle_height // 2
    paddle_x = 50

    pad_size = paddle_width, paddle_height

    pad_window_size = paddle_width * 3, window_size[1]

    windows = [
        game_window(
            position=(0, 0),
            size=pad_window_size,
            pinned=True,
        ),
        game_window(
            position=(window_size[0] - pad_window_size[0], 0),
            size=pad_window_size,
            pinned=True,
        ),
        game_window(centered=True),
        game_window(),
        game_window(),
        game_window(),
        game_window(),
    ]

    window_infos = list(repeat(None, len(windows)))

    # Instead of recalculating the borders offset with the ball radius, just
    # calculate them once here. A ball of radius R bouncing off a rectangle of
    # size (W, H) is equivalent to an infintesimally small ball bouncing off a
    # rectangle of size (W - 2R, H - 2R) anyway.
    ball_area_rect = (
        paddle_x + paddle_width + ball_radius,
        ball_radius,
        window_size[0] - (game.PADDLE_X + game.PADDLE_WIDTH + ball_radius) * 2,
        window_size[1] - 20 - ball_radius * 2,
    )

    score = 0
    highscore = 0

    while True:
        time.sleep(frame_length)

        ball_pos = (
            ball_pos[0] + ball_speed * frame_length * ball_dir[0],
            ball_pos[1] + ball_speed * frame_length * ball_dir[1],
        )

        if ball_pos[0] < ball_area_rect[0]:
            # Bounced off the left: `score` + 1
            score += 1
            ball_dir = (1, ball_dir[1])
        elif ball_pos[0] > ball_area_rect[0] + ball_area_rect[2]:
            # Bounced off the right: `score` + 1
            score += 1
            ball_dir = (-1, ball_dir[1])
        elif ball_pos[1] < ball_area_rect[1]:
            ball_dir = (ball_dir[0], 1)
        elif ball_pos[1] > ball_area_rect[1] + ball_area_rect[3]:
            ball_dir = (ball_dir[0], -1)

        renderables = [
            render.Circle(ball_pos, ball_radius),
            render.Rectangle(
                (
                    paddle_x,
                    ball_pos[1] - half_paddle_height,
                ),
                pad_size,
            ),
            render.Rectangle(
                (
                    window_size[0] - paddle_x - paddle_width,
                    ball_pos[1] - half_paddle_height,
                ),
                pad_size,
            ),
            render.Text(
                (0, 0),
                "SCORE: {}".format(score),
            ),
            render.Text(
                (0, 20),
                "HIGH: {}".format(highscore),
            ),
        ]

        for (infos, (g, _)) in zip(window_infos, windows):
            if infos is not None and physics.contains(
                inner=ball_pos,
                outer=(infos.x, infos.y, infos.width, infos.height),
            ):
                to_send = [messages.freeze()]
            else:
                to_send = [messages.unfreeze()]

            to_send.append(messages.render(renderables))

            print(to_send)

            g.send(to_send)

        msgs = list(map(lambda (chan, _): chan.recv(), windows))

        # Evaluate this first so you don't lose by closing a window containing
        # a ball
        ended = any(filter(messages.is_quit, msgs))

        game_lost = False
        if not ended:
            rectangles = map(
                lambda m: m.info,
                filter(messages.is_client_state, msgs),
            )

            window_infos = rectangles

            game_lost = not any(
                filter(
                    lambda rec: physics.contains(
                        inner=ball_pos,
                        outer=(rec.x, rec.y, rec.width, rec.height),
                    ),
                    rectangles
                )
            )

            if game_lost:
                print("You lost :(")
                ended = True

        if ended:
            for (g, _) in windows:
                g.send(messages.quit())
            return game_lost
        else:
            pass

if __name__ == '__main__':
    while main():
        pass
