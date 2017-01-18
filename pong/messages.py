from collections import namedtuple

Message = namedtuple('Message', ('type', 'info'))

QUIT = 'quit'
ACTION = 'action'

def action(info):
    return Message(type=ACTION, info=info)

def quit():
    return Message(type=QUIT, info=None)

def is_quit(msg):
    return isinstance(msg, Message) and msg.type == QUIT
