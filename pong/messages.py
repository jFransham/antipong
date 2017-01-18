from collections import namedtuple

Message = namedtuple('Message', ('type', 'window_handle', 'event_info'))

QUIT = 'quit'
NOOP = 'noop'

def noop(window_info):
    return Message(type=NOOP, window_handle=window_handle, event_info=None)

def quit():
    return Message(type=QUIT, window_handle=None, event_info=None)

def is_quit(msg):
    return msg.type == QUIT
