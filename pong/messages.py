from collections import namedtuple

Message = namedtuple('Message', ('type', 'window_handle', 'event_info'))

QUIT = 'quit'
NOOP = 'noop'

def noop(window_handle):
    return Message(type=NOOP, window_info=window_info, event_info=None)

def quit():
    return Message(type=QUIT, window_info=None, event_info=None)

def is_quit(msg):
    return msg.type == QUIT
