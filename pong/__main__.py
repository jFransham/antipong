"""
Python antipong.

How to play: Move the windows so that the ball is always visible on at least
             one of them.

             You score by letting the ball bounce off one of the paddles.

             To increase difficulty, buy a bigger monitor.
"""

from __future__ import absolute_import

import sys
import os
import time
import pygame
import getopt

from itertools import repeat, chain
from multiprocessing import Process, Pipe
from collections import namedtuple

from . import messages, game, render, physics

DEFAULT_TARGET_FPS = 60
DEFAULT_INITIAL_BALL_SPEED = 70
DEFAULT_BALL_SPEED_SCORE_MULTIPLIER = 10
DEFAULT_BALL_RADIUS = 10
DEFAULT_NUM_MOVABLE_WINDOWS = 5
DEFAULT_PADDLE_X = 50
DEFAULT_PADDLE_SIZE = (30, 100)
DEFAULT_SCOREFILE_PATH = './score.txt'

Options = namedtuple(
    'Options',
    [
        'target_fps',
        'initial_ball_speed',
        'ball_speed_score_multiplier',
        'ball_radius',
        'num_movable_windows',
        'paddle_x',
        'paddle_size',
        'scorefile_path',
    ]
)


def options(**kwargs):
    defaults = dict(
        target_fps=DEFAULT_TARGET_FPS,
        initial_ball_speed=DEFAULT_INITIAL_BALL_SPEED,
        ball_speed_score_multiplier=DEFAULT_BALL_SPEED_SCORE_MULTIPLIER,
        ball_radius=DEFAULT_BALL_RADIUS,
        num_movable_windows=DEFAULT_NUM_MOVABLE_WINDOWS,
        paddle_x=DEFAULT_PADDLE_X,
        paddle_size=DEFAULT_PADDLE_SIZE,
        scorefile_path=DEFAULT_SCOREFILE_PATH,
    )

    # Merge two dictionaries
    out_args = dict(
        chain(
            defaults.items(),
            kwargs.items(),
        )
    )

    return Options(**out_args)


def subprocess(fn):
    my_conn, child_conn = Pipe()

    proc = Process(target=fn, args=(child_conn,))
    proc.start()

    return (my_conn, proc)


def get_width_height():
    """
    Gets the width and height of the current display
    """

    # We have to open a window before `Info`, otherwise it grabs the whole
    # screen and opening windows in the subprocesses stops working properly.
    # No arguments means fullscreen by default.
    pygame.display.set_mode()

    info = pygame.display.Info()
    out = info.current_w, info.current_h

    # Close the window again, since we don't need it
    pygame.display.quit()
    return out


def mk_renderables(
    ball_pos,
    score,
    highscore,
    display_size,
    options,
    fps=None,
):
    """
    Builds the `Renderable` objects to send to the child processes for a given
    frame.

    :param fps: If None, the FPS counter will not be shown.
    """

    paddle_width, paddle_height = options.paddle_size
    half_paddle_height = paddle_height // 2

    out = [
        render.Circle(ball_pos, options.ball_radius),
        render.Rectangle(
            (
                options.paddle_x,
                ball_pos[1] - half_paddle_height,
            ),
            options.paddle_size,
        ),
        render.Rectangle(
            (
                display_size[0] - options.paddle_x - paddle_width,
                ball_pos[1] - half_paddle_height,
            ),
            options.paddle_size,
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


def mk_windows(
    display_size,
    pad_window_size,
    options,
):
    """
    Spawns the subprocesses and returns an array of (channel, process) tuples.

    :param display_size: The size of the display. This doesn't have to actually
                         correspond to the pixels on the current display, and
                         can be an arbitrary number.
    """
    # This game is actually unplayable with less than 2 windows, but
    # technically the code doesn't assume any more than 1, so if you want to be
    # sadistic then go crazy.
    assert options.num_movable_windows >= 1

    left_paddle_window = game.mk_game_process(
        position=(0, 0),
        size=pad_window_size,
        pinned=True,
    )

    right_paddle_window = game.mk_game_process(
        position=(display_size[0] - pad_window_size[0], 0),
        size=pad_window_size,
        pinned=True,
    )

    out = [
        subprocess(left_paddle_window),
        subprocess(right_paddle_window),
    ]
    movable_window = game.mk_game_process()

    out.append(subprocess(game.mk_game_process(centered=True)))
    # Subtract one, because the first one is the centered one on the previous
    # line
    out.extend(
        map(
            subprocess,
            repeat(movable_window, options.num_movable_windows - 1)
        )
    )

    return out


def update_ball_position(position, speed, direction, dt):
    """
    """
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


def play_area(display_size, options):
    side_offset = (
        options.paddle_x + options.paddle_size[0] + options.ball_radius
    )

    return (
        side_offset,
        options.ball_radius,
        display_size[0] - side_offset * 2,
        display_size[1] - 20 - options.ball_radius * 2,
    )


def handle_ball_physics(position, speed, direction, dt, play_area):
    inc_score = False
    out_dir = None
    out_pos = update_ball_position(position, speed, direction, dt)

    if direction[0] < 0 and position[0] < play_area[0]:
        # Bounced off the left: `score` + 1
        inc_score = True
        out_dir = (1, direction[1])
    elif direction[0] > 0 and position[0] > play_area[0] + play_area[2]:
        # Bounced off the right: `score` + 1
        inc_score = True
        out_dir = (-1, direction[1])
    elif direction[1] < 0 and position[1] < play_area[1]:
        out_dir = (direction[0], 1)
    elif direction[1] > 0 and position[1] > play_area[1] + play_area[3]:
        out_dir = (direction[0], -1)
    else:
        out_dir = direction

    return out_pos, out_dir, inc_score


def rolling_average(average, current, multiplier=0.1):
    """
    Calculate a rolling average by adding a proportion of the difference with
    each new value.
    """

    return average + (current - average) * multiplier


def run_game(highscore, options=options()):
    frame_length = 1.0 / options.target_fps
    paddle_width = options.paddle_size[0]

    display_size = get_width_height()
    ball_pos = display_size[0] // 2, display_size[1] // 2
    ball_dir = 1, 1
    pad_window_size = paddle_width * 3, display_size[1]

    windows = mk_windows(display_size, pad_window_size, options=options)

    window_infos = list(repeat(None, len(windows)))

    # Instead of recalculating the borders offset with the ball radius, just
    # calculate them once here. A ball of radius R bouncing off a rectangle of
    # size (W, H) is equivalent to an infintesimally small ball bouncing off a
    # rectangle of size (W - 2R, H - 2R) anyway.
    ball_area_rect = play_area(display_size, options=options)

    score = 0
    last_time = time.time() - frame_length
    avg_fps = options.target_fps

    while True:
        cur_time = time.time()
        dt = cur_time - last_time
        fps = 1.0 / dt
        avg_fps = rolling_average(avg_fps, fps)
        last_time = cur_time

        ball_speed = (
            options.initial_ball_speed +
            score * options.ball_speed_score_multiplier
        )

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
            options=options,
            fps=int(round(avg_fps)),
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

        post_time = time.time()
        process_time = post_time - cur_time
        time.sleep(max(frame_length - process_time, 0))


if __name__ == '__main__':
    def args_to_options_dict_elements(arg):
        name, val = arg

        if name in ('-w', '--windows'):
            return ('num_movable_windows', int(val))
        elif name in ('-s', '--speed'):
            return ('ball_speed', int(val))
        elif name in ('-m', '--multiplier'):
            return ('ball_speed_score_multiplier', int(val))
        elif name in ('-o', '--scorefile'):
            return ('scorefile_path', int(val))
        else:
            return None

    docstring = (
        'Possible options:\n'
        '    -w, --windows     Set number of movable game windows '
        '(minimum 1, default {num_windows})\n'
        '    -s, --speed       Set initial ball speed (default '
        '{ball_speed})\n'
        '    -m, --multiplier  Set amount ball speed increases with '
        'each bounce off the paddles (default {ball_multiplier})\n'
        '    -o, --scorefile   Set the path where highscores will be'
        '                      written (default {scorefile})\n'
    ).format(
        num_windows=DEFAULT_NUM_MOVABLE_WINDOWS,
        ball_speed=DEFAULT_INITIAL_BALL_SPEED,
        ball_multiplier=DEFAULT_BALL_SPEED_SCORE_MULTIPLIER,
        scorefile=DEFAULT_SCOREFILE_PATH,
    )

    try:
        opts, argv = getopt.getopt(
            sys.argv[1:],
            'w:s:m:o:',
            ['windows=', 'speed=', 'multiplier=', 'scorefile='],
        )
    except getopt.GetoptError:
        print(docstring)
        sys.exit()

    opts_args = dict(
        filter(
            lambda x: x is not None,
            map(
                args_to_options_dict_elements,
                opts
            )
        )
    )

    options = options(**opts_args)

    high = 0
    if os.path.isfile(options.scorefile_path):
        with open(options.scorefile_path, 'r') as score_file:
            high = int(score_file.read())

    while True:
        score = run_game(high, options)

        if score is None:
            break

        high = max(score, high)

    with open('score.txt', 'w') as score_file:
        score_file.write(str(high))
