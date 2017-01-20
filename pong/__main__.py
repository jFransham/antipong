"""
Python antipong.
"""

from __future__ import absolute_import

import time
import pygame

from . import messages, game, render, physics

from itertools import repeat
from multiprocessing import Process, Pipe

FRAME_LENGTH = 1.0 / 60.0
INITIAL_BALL_SPEED = 70
BALL_SPEED_SCORE_MULTIPLIER = 10
BALL_RADIUS = 10
PADDLE_HEIGHT = 100
PADDLE_WIDTH = 30
HALF_PADDLE_HEIGHT = PADDLE_HEIGHT // 2
PADDLE_X = 50
PADDLE_SIZE = PADDLE_WIDTH, PADDLE_HEIGHT


def game_window(*args, **kwargs):
    my_conn, child_conn = Pipe()

    game_fn = game.mk_game_process(*args, **kwargs)

    proc = Process(target=game_fn, args=(child_conn,))
    proc.start()

    return (my_conn, proc)


# TODO: This craps out if I try to open a window in another thread, what
#       happens if I open a window in this thread _first_?
def get_width_height():
    pygame.display.set_mode()
    info = pygame.display.Info()
    out = info.current_w, info.current_h
    pygame.display.quit()
    return out


def mk_renderables(ball_pos, score, highscore, display_size, fps=None):
    out = [
        render.Circle(ball_pos, BALL_RADIUS),
        render.Rectangle(
            (
                PADDLE_X,
                ball_pos[1] - HALF_PADDLE_HEIGHT,
            ),
            PADDLE_SIZE,
        ),
        render.Rectangle(
            (
                display_size[0] - PADDLE_X - PADDLE_WIDTH,
                ball_pos[1] - HALF_PADDLE_HEIGHT,
            ),
            PADDLE_SIZE,
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

    if fps is not None:
        out.append(
            render.Text(
                (display_size[0] - 90, 0),
                "FPS: {}".format(fps),
            )
        )

    return out


def mk_windows(display_size, pad_window_size):
    return [
        game_window(
            position=(0, 0),
            size=pad_window_size,
            pinned=True,
        ),
        game_window(
            position=(display_size[0] - pad_window_size[0], 0),
            size=pad_window_size,
            pinned=True,
        ),
        game_window(centered=True),
        game_window(),
        game_window(),
        game_window(),
        game_window(),
    ]


def update_ball(position, speed, direction, dt):
    return (
        position[0] + speed * dt * direction[0],
        position[1] + speed * dt * direction[1],
    )


# TODO: Should this call `mk_renderables` instead of taking it as an argument?
def update_windows(windows, window_infos, renderables, ball_pos):
    for (infos, (g, _)) in zip(window_infos, windows):
        if infos is not None and physics.contains(
            inner=ball_pos,
            outer=(infos.x, infos.y, infos.width, infos.height),
        ):
            to_send = [messages.freeze()]
        else:
            to_send = [messages.unfreeze()]

        to_send.append(messages.render(renderables))

        g.send(to_send)


def play_area(display_size):
    return (
        PADDLE_X + PADDLE_WIDTH + BALL_RADIUS,
        BALL_RADIUS,
        display_size[0] - (PADDLE_X + PADDLE_WIDTH + BALL_RADIUS) * 2,
        display_size[1] - 20 - BALL_RADIUS * 2,
    )


def handle_ball_physics(position, speed, direction, dt, play_area):
    inc_score = False
    out_dir = None
    out_pos = update_ball(position, speed, direction, dt)

    if position[0] < play_area[0]:
        # Bounced off the left: `score` + 1
        inc_score = True
        out_dir = (1, direction[1])
    elif position[0] > play_area[0] + play_area[2]:
        # Bounced off the right: `score` + 1
        inc_score = True
        out_dir = (-1, direction[1])
    elif position[1] < play_area[1]:
        out_dir = (direction[0], 1)
    elif position[1] > play_area[1] + play_area[3]:
        out_dir = (direction[0], -1)
    else:
        out_dir = direction

    return out_pos, out_dir, inc_score


def run_game(highscore):
    display_size = get_width_height()
    ball_pos = display_size[0] // 2, display_size[1] // 2
    ball_dir = 1, 1
    pad_window_size = PADDLE_WIDTH * 3, display_size[1]

    windows = mk_windows(display_size, pad_window_size)

    window_infos = list(repeat(None, len(windows)))

    # Instead of recalculating the borders offset with the ball radius, just
    # calculate them once here. A ball of radius R bouncing off a rectangle of
    # size (W, H) is equivalent to an infintesimally small ball bouncing off a
    # rectangle of size (W - 2R, H - 2R) anyway.
    ball_area_rect = play_area(display_size)

    score = 0
    last_time = time.time()

    while True:
        cur_time = time.time()
        dt = cur_time - last_time
        last_time = cur_time

        time.sleep(max(FRAME_LENGTH - dt, 0))

        ball_speed = INITIAL_BALL_SPEED + score * BALL_SPEED_SCORE_MULTIPLIER

        ball_pos, ball_dir, inc_score = handle_ball_physics(
            position=ball_pos,
            speed=ball_speed,
            direction=ball_dir,
            dt=dt,
            play_area=ball_area_rect,
        )

        if inc_score:
            score += 1

        renderables = mk_renderables(
            ball_pos=ball_pos,
            score=score,
            highscore=highscore,
            display_size=display_size,
            fps=1.0 / dt,
        )

        update_windows(
            windows=windows,
            window_infos=window_infos,
            renderables=renderables,
            ball_pos=ball_pos,
        )

        msgs = list(
            map(
                lambda chans: chans[0].recv(),
                windows,
            )
        )

        # Evaluate this first so you don't lose by closing a window containing
        # a ball
        ended = any(filter(messages.is_quit, msgs))

        game_lost = False
        if not ended:
            window_infos = map(
                lambda m: m.info,
                filter(messages.is_client_state, msgs),
            )

            game_lost = not physics.any_contains(
                inner=ball_pos,
                outers=map(
                    lambda info: (info.x, info.y, info.width, info.height),
                    window_infos,
                )
            )

            if game_lost:
                print("You lost :(")
                ended = True

        if ended or game_lost:
            for (g, _) in windows:
                g.send([messages.quit()])

            if game_lost:
                return score
            else:
                return None
        else:
            pass


if __name__ == '__main__':
    high = 0

    while True:
        score = run_game(high)

        if score is None:
            break

        high = max(score, high)
