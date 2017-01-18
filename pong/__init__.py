"""
Python antipong.
"""

from __future__ import absolute_import

import sys
import pygame

from . import messages, windowing

from multiprocessing import Process, Pipe
from collections import namedtuple

def mk_subprocess(fn, chan):
    for i in fn():
        chan.send(i)

        if messages.is_quit(i):
            return

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

    def game_process():
        """
        XXX
        Game terminal iterator. Might convert this to not be an iterator any
        more, since the behaviour being abstracted here is trivial.
        """
        pygame.init()
        screen = pygame.display.set_mode(size)
        pin = None

        while True:
            win_info = windowing.get_win_info(
                pygame.display.get_wm_info()['window']
            )

            if pin:


            if any(pygame.event.get(pygame.QUIT)):
                yield messages.quit()

            yield messages.noop()

    return game_process

def main():
    my_conn, child_conn = Pipe()

    game = mk_game_process(None)

    proc = Process(target=mk_subprocess, args=(game, child_conn,))
    proc.daemon = True
    proc.start()

    while True:
        msg = my_conn.recv()

        if messages.is_quit(msg):
            print('Quitting')
            sys.exit()
        else:
            print()
