#!/bin/python2.7

"""
Python antipong.

How to play: Move the windows so that the ball is always visible on at least
             one of them.

             You score by letting the ball bounce off one of the paddles.

             To increase difficulty, buy a bigger monitor.
"""

import sys
import os
import time
import math
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
DEFAULT_PADDLE_SIZE = 30, 100
DEFAULT_SCOREFILE_PATH = './score.txt'
DEFAULT_MOVABLE_WINDOW_SIZE = 300, 300

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
        'display_size',
        'movable_window_size'
    ]
)


DISPLAY_SIZE = None


def memoized_display_size():
    """
    Get the display size as first calculated by this program. The weird name is
    to make it explicit that this is not recalculated when the program changes
    displays.

    :return: An integer tuple of (display width, display height)
    """

    global DISPLAY_SIZE

    if DISPLAY_SIZE is None:
        DISPLAY_SIZE = display_size()

    return DISPLAY_SIZE


def options(**kwargs):
    """
    Generate an `Options` structure, with any unsupplied parameters being
    filled in by defaults. This can also be acheived by overriding
    `Options.__new__.__defaults__`, but I'm going to avoid that option since I
    don't want to go to hell today.

    NOTE: This is used as a default argument for `run_game`, so it _MUST_ be
          idempotent (and, ideally, pure).

    Possible arguments to this function precisely match the field names for
    `Options`. You can only supply these as named parameters, to simplify the
    implementation of this function (if we wanted to supply positional
    arguments too we could just use
    `map(lambda a, b: a if a is not None else b, args, defaults.values())`).
    """

    defaults = dict(
        target_fps=DEFAULT_TARGET_FPS,
        initial_ball_speed=DEFAULT_INITIAL_BALL_SPEED,
        ball_speed_score_multiplier=DEFAULT_BALL_SPEED_SCORE_MULTIPLIER,
        ball_radius=DEFAULT_BALL_RADIUS,
        num_movable_windows=DEFAULT_NUM_MOVABLE_WINDOWS,
        paddle_x=DEFAULT_PADDLE_X,
        paddle_size=DEFAULT_PADDLE_SIZE,
        scorefile_path=DEFAULT_SCOREFILE_PATH,
        movable_window_size=DEFAULT_MOVABLE_WINDOW_SIZE,
        display_size=None,
    )

    # Merge two dictionaries
    out_args = dict(
        chain(
            defaults.items(),
            kwargs.items(),
        )
    )

    return Options(**out_args)


def subprocess(game_process):
    """
    Create a subprocess that runs a `GameProcess`

    :param game_process: An instance of `GameProcess`
    :return:             A tuple of (pipe endpoint, process)
    """

    my_conn, child_conn = Pipe()

    proc = Process(target=game.run_process, args=(game_process, child_conn,))
    proc.start()

    return my_conn, proc


def display_size():
    """
    Gets the width and height of the current display

    :return: A tuple of (width, height)
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
    last_score,
    display_size,
    options,
    fps=None,
    time_left=None,
):
    """
    Builds the `Renderable` objects to send to the child processes for a given
    frame.

    :param ball_pos:      A two-element integer tuple of the position of the
                          ball.
    :param score:         An integer of the game's current score
    :param highscore:     An integer of the player's current best score
    :param display_size:  An integer tuple of (display width, display height)
    :param fps:           An integer representing FPS, or None. If None, the
                          FPS counter will not be shown
    :return:              A list of `Renderable`s
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
            "HIGH:  {}".format(highscore),
        ),
    ]

    if last_score is not None:
        out.append(
            render.Text(
                (0, 40),
                "LAST:  {}".format(last_score),
            )
        )

    if fps is not None:
        out.append(
            render.Text(
                (display_size[0] - 90, 0),
                "FPS: {}".format(fps),
            )
        )

    if time_left is not None:
        out.append(
            render.Text(
                (
                    display_size[0] // 2 + options.ball_radius,
                    display_size[1] // 2 + options.ball_radius,
                ),
                str(int(math.ceil(time_left))),
            )
        )

    return out


def mk_windows(
    display_size,
    paddle_window_size,
    options,
):
    """
    Spawns subprocesses with each of the game windows

    :param display_size:       A two-element integer tuple representing the
                               size of the display. This doesn't have to
                               actually correspond to the pixels available on
                               the current display, as long as it is consistent
                               throughout the program
    :param paddle_window_size: A two-element integer tuple of the size of the
                               immovable windows at the left- and right-hand
                               sides of the game area
    :param options:            An `Options` object
    :return:                   A list of channels to communicate with the child
                               processes
    """
    # This game is actually unplayable with less than 2 windows, but
    # technically the code doesn't assume any more than 1, so if you want to be
    # sadistic then go crazy.
    assert options.num_movable_windows >= 1

    left_paddle_window = game.GameProcess(
        position=(0, 0),
        size=paddle_window_size,
        pinned=True,
    )

    right_paddle_window = game.GameProcess(
        position=(display_size[0] - paddle_window_size[0], 0),
        size=paddle_window_size,
        pinned=True,
    )

    out = [
        subprocess(left_paddle_window),
        subprocess(right_paddle_window),
    ]

    # NOTE: I calculate this manually instead of just using `centered=True` to
    #       ensure that at least one window is in the center of the game area
    #       at the start (since the game area may not be centered on the center
    #       of the screen, or SDL may not be able to request a centered window)
    out.append(
        subprocess(
            game.GameProcess(
                position=(
                    (display_size[0] - options.movable_window_size[0]) // 2,
                    (display_size[1] - options.movable_window_size[1]) // 2,
                ),
                size=options.movable_window_size,
            )
        )
    )

    movable_window = game.GameProcess(size=options.movable_window_size)
    # Subtract one, because the first one is the centered one on the previous
    # line
    out.extend(
        map(
            subprocess,
            repeat(movable_window, options.num_movable_windows - 1)
        )
    )

    return out


def tick_position(position, speed, direction, dt):
    """
    Advances position a single tick

    :param position:  A two-element float tuple of the current position
    :param speed:     A float representing the current speed, in units of
                      pixels * sqrt(2)
    :param direction: A two-element numerical tuple of the current movement
                      direction. Both elements should be one of [-1, 1]
    """

    # TODO: Should `direction` be normalised to support balls going in
    #       arbitrary directions? Could lead to some wacky multiball fun.
    return (
        position[0] + speed * dt * direction[0],
        position[1] + speed * dt * direction[1],
    )


def try_recv(chan, consume=False):
    """
    Non-blocking version of `Channel.recv`
    """
    if chan.poll():
        return consume_channel_buffer(chan) if consume else chan.recv()
    else:
        return None


def consume_channel_buffer(chan):
    out = chan.recv()
    while chan.poll():
        out = chan.recv()

    return out


# TODO: Should this call `mk_renderables` instead of taking it as an argument?
def update_windows(windows, renderables, ball_pos, should_block=False):
    """
    Sends one tick's worth of messages to the child windows, and return the
    result. It will freeze/unfreeze children based on the ball's position, and
    render all the objects on screen.

    NOTE: If one of the processes is not responding to messages this will
          block after a couple of seconds as the connection's buffer fills up.
          The correct way to fix this is to use a version of connection that
          has a ring buffer instead of a blocking buffer. There doesn't seem to
          be a process-aware non-blocking ring buffer in Python's stdlib
          (`collections.deque` comes close, but is single-process only, and
          `multiprocessing.Queue` blocks when full) and writing one is out of
          scope for this project.

          Keeping this update loop non-blocking is actually really important,
          because `pygame` (maybe `SDL`?) will block when moving the window on
          Windows. This seems to be related to Windows's blocking event loop,
          although it could probably be circumvented if `pygame`/`SDL` was
          designed with it in mind.

    :param windows:     A list of two-element tuples (channel, window info)
    :param renderables: A list of `Renderable`s. These must be picklable
    :param ball_pos:    A two element tuple of the ball's current position
    :return:            A list of responses from the windows
    """

    for (chan, infos) in windows:
        if infos is not None and physics.contains(
            inner=ball_pos,
            outer=(infos.x, infos.y, infos.width, infos.height),
        ):
            to_send = [messages.freeze()]
        else:
            to_send = [messages.unfreeze()]

        to_send.append(messages.render(renderables))

        chan.send(to_send)

    # Pass this to `list` to force all the `recv` calls at the same time (to
    # avoid confusing behaviour if we pass this to a function that doesn't
    # consume the whole list, or suchlike).
    # Additionally, we use blocking `recv` if there is no existing window info,
    # since we can't do anything at all if we've never received window size/pos
    # information for a given window. Otherwise, non-blocking `recv` is used.
    if should_block:
        return list(
            map(
                lambda (chan, info): consume_channel_buffer(chan),
                windows,
            )
        )
    else:
        return list(
            map(
                lambda chan: try_recv(chan[0], consume=True),
                windows,
            )
        )


def play_area(display_size, options):
    """
    Gets the area that represents legal values for the ball's position

    :param display_size: A two-element integer tuple representing the total
                         visible size of the game
    :param options:      An `Options` object
    """
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
    out_pos = tick_position(position, speed, direction, dt)

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

    :param average:    The existing average
    :param current:    The latest value
    :param multiplier: The amount to change the average with each new value
    :return:           The new average
    """
    return average + (current - average) * multiplier


def unzip(tuple_list):
    """
    Converts an enumerable of tuples to a tuple of lists

    :param tuple_list: An enumerable of tuples
    :return:           A tuple of length `min(map(len, tuple_list))``
    """
    return tuple(map(list, zip(*tuple_list)))


def run_game(last_score, highscore, options=options()):
    """
    Run a single instance of the game, and tear down when finished.

    :param highscore: The maximum score acheived by the player.
    :param options:   An `Options` object
    """

    display_size = (
        options.display_size
        if options.display_size is not None
        else memoized_display_size()
    )
    frame_length = 1.0 / options.target_fps
    paddle_width = options.paddle_size[0]
    pause_time = 3

    ball_pos = display_size[0] // 2, display_size[1] // 2
    ball_dir = 1, 1
    pad_window_size = paddle_width * 3, display_size[1]

    chans, procs = unzip(
        mk_windows(
            display_size,
            pad_window_size,
            options=options,
        )
    )

    window_infos = list(repeat(None, len(chans)))
    first_iteration = True

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

        while dt > 0:
            step_dt = min(dt, frame_length)

            if pause_time is None:
                ball_speed = (
                    options.initial_ball_speed +
                    score * options.ball_speed_score_multiplier
                )

                ball_pos, ball_dir, inc_score = handle_ball_physics(
                    position=ball_pos,
                    speed=ball_speed,
                    direction=ball_dir,
                    dt=step_dt,
                    play_area=ball_area_rect,
                )

                if inc_score:
                    score += 1
            else:
                pause_time -= step_dt

                if pause_time <= 0:
                    pause_time = None

            dt -= frame_length

        renderables = mk_renderables(
            ball_pos=ball_pos,
            score=score,
            highscore=highscore,
            last_score=last_score,
            display_size=display_size,
            options=options,
            fps=int(round(avg_fps)),
            time_left=pause_time,
        )

        msgs = update_windows(
            windows=zip(chans, window_infos),
            renderables=renderables,
            ball_pos=ball_pos,
            should_block=first_iteration,
        )

        window_infos = map(
            lambda (m, last): (
                m.info
                if messages.is_client_state(m)
                else last
            ),
            zip(msgs, window_infos),
        )

        # Don't check if game is lost if the game hasn't started yet - this is
        # mostly so you don't get stuck in an infinite loop if the ball doesn't
        # spawn in a window for whatever reason
        game_lost = pause_time is None and not physics.any_contains(
            inner=ball_pos,
            outers=map(
                lambda info: (info.x, info.y, info.width, info.height),
                window_infos,
            )
        )

        # NOTE: Ideally we'd only use message-passing here to exit gracefully,
        #       but we can't handle SIGHUP and friends so we'll exit if one of
        #       our children dies unexpectedly
        ended = game_lost or (
            any(filter(messages.is_quit, msgs)) or
            any(filter(lambda p: not p.is_alive(), procs))
        )

        if ended:
            for chan in chans:
                chan.send([messages.quit()])

            if game_lost:
                return score
            else:
                return None
        else:
            pass

        post_time = time.time()
        process_time = post_time - cur_time
        time.sleep(max(frame_length - process_time, 0))

        first_iteration = False


def typed_tuple(typ, n=None):
    """
    Makes a function turning a string into a typed tuple of elements.

    :param typ: The type of the elements
    :param n:   The number of elements in the tuple (or None if it can be any
                length)
    :return:    A function converting a string to a tuple
    """
    def typed_tuple_inner(s):
        split = s.split(',')

        if n is not None:
            assert len(split) == n

        return tuple(map(typ, split))

    return typed_tuple_inner


def args_to_options_dict_elements(flagdefs):
    def args_to_dict_inner(arg):
        name, val = arg

        for flagdef in flagdefs:
            if flagdef.in_output and (
                name == '-{}'.format(flagdef.short_flag) or
                name == '--{}'.format(flagdef.long_flag)
            ):
                return flagdef.field_name, flagdef.field_type(val)

        return None

    return args_to_dict_inner


if __name__ == '__main__':
    CmdFlags = namedtuple(
        'CmdFlags',
        (
            'short_flag',
            'long_flag',
            'field_name',
            'field_type',
            'help_text',
            'in_output',
        ),
    )

    # These are hardcoded into getopt, so they're only supplied in `flags` to
    # show up in the docstring
    short_help = 'h'
    long_help = 'help'

    flags = [
        CmdFlags(
            'w', 'windows', 'num_movable_windows', int,
            'Set number of movable game windows (minimum 1, default '
            '{})'.format(
                DEFAULT_NUM_MOVABLE_WINDOWS
            ),
            in_output=True,
        ),
        CmdFlags(
            'z', 'window_size', 'movable_window_size', typed_tuple(int, n=2),
            'Set the size of the movable game windows (default {})'.format(
                DEFAULT_MOVABLE_WINDOW_SIZE
            ),
            in_output=True,
        ),
        CmdFlags(
            's', 'speed', 'ball_speed', int,
            'Set initial ball speed (default {})'.format(
                DEFAULT_INITIAL_BALL_SPEED
            ),
            in_output=True,
        ),
        CmdFlags(
            'm', 'multiplier', 'ball_speed_score_multiplier', int,
            'Set amount ball speed increases with each bounce off the paddles'
            '(default {})'.format(
                DEFAULT_BALL_SPEED_SCORE_MULTIPLIER
            ),
            in_output=True,
        ),
        CmdFlags(
            'o', 'scorefile', 'scorefile_path', str,
            'Set the path where highscores will be written (default '
            '{})'.format(
                DEFAULT_SCOREFILE_PATH
            ),
            in_output=True,
        ),
        CmdFlags(
            's', 'displaysize', 'display_size', typed_tuple(int, n=2),
            'Set the display size of the game - if not set, will be inferred',
            in_output=True,
        ),
        CmdFlags(
            short_help, long_help, None, None,
            'Show this message',
            in_output=False,
        ),
    ]

    docstring = (
        'Possible options:\n' +
        '\n'.join(
            map(
                lambda flag: (
                    '    -{}, --{}\n        {}'.format(
                        flag.short_flag,
                        flag.long_flag,
                        flag.help_text,
                    )
                ),
                flags,
            )
        )
    )

    shortopts = ''.join(
        map(
            lambda flag: flag.short_flag + ':',
            flags
        )
    )

    longopts = list(
        map(
            lambda flag: flag.long_flag + '=',
            flags
        )
    )

    try:
        opts, argv = getopt.getopt(
            sys.argv[1:],
            shortopts,
            longopts,
        )
    except getopt.GetoptError:
        print(docstring)
        sys.exit(2)

    opts_args = dict(
        filter(
            lambda x: x is not None,
            map(
                args_to_options_dict_elements(flags),
                opts
            )
        )
    )

    options = options(**opts_args)

    high = 0
    if os.path.isfile(options.scorefile_path):
        with open(options.scorefile_path, 'r') as score_file:
            high = int(score_file.read())

    score = None

    while True:
        score = run_game(score, high, options)

        if score is None:
            break

        high = max(score, high)

    with open('score.txt', 'w') as score_file:
        score_file.write(str(high))
