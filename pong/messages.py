from collections import namedtuple

# NOTE: Throughout this program we use `==` to compare opaque singletons. If we
#       were in a single process we would be better off with `is` (since we
#       can't get false positives by using literals that happen to coincide
#       with the singleton's inner value) but there's no ensuring that
#       different processes' view of the singletons point to the same object,
#       and without the presence of shared memory we can only assume that they
#       do not.

Message = namedtuple('Message', ('type', 'info'))

# TODO: String idents are just for debugging, convert these to `gen_ident`
#       function that returns an opaque integer (can't use opaque object, see
#       note)
QUIT = 'quit'
RENDER = 'render'
FREEZE = 'freeze'
UNFREEZE = 'unfreeze'
CLIENT_STATE = 'client_state'

def client_state(info):
    return Message(type=CLIENT_STATE, info=info)

def render(info):
    return Message(type=RENDER, info=info)

def freeze():
    return Message(type=FREEZE, info=None)

def unfreeze():
    return Message(type=UNFREEZE, info=None)

def quit():
    return Message(type=QUIT, info=None)

def is_quit(msg):
    return isinstance(msg, Message) and msg.type == QUIT

def is_render(msg):
    return isinstance(msg, Message) and msg.type == RENDER

def is_freeze(msg):
    return isinstance(msg, Message) and msg.type == FREEZE

def is_unfreeze(msg):
    return isinstance(msg, Message) and msg.type == UNFREEZE

def is_client_state(msg):
    return isinstance(msg, Message) and msg.type == CLIENT_STATE
