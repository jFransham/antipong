import pygame

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DEFAULT_FONT = None
DEFAULT_FONT_SIZE = 15

def default_font():
    global DEFAULT_FONT

    if DEFAULT_FONT is None:
        DEFAULT_FONT = pygame.font.SysFont('monospace', DEFAULT_FONT_SIZE)

    return DEFAULT_FONT

class Renderable(object):
    position = None

    def __init__(self, pos):
        self.position = pos

    def render(self, surface, offset):
        raise NotImplementedError()

class Circle(Renderable):
    radius = None

    def __init__(self, pos, radius):
        super(Circle, self).__init__(pos)
        self.radius = radius

    def __eq__(self, other):
        return isinstance(other, Circle) and (
            self.radius == other.radius and
            self.position == other.position
        )

    def render(self, surface, offset):
        pygame.draw.circle(
            surface,
            WHITE,
            (
                int(self.position[0] - offset[0]),
                int(self.position[1] - offset[1]),
            ),
            self.radius,
        )

class Rectangle(Renderable):
    size = None

    def __init__(self, pos, size):
        super(Rectangle, self).__init__(pos)
        self.size = size

    def __eq__(self, other):
        return isinstance(other, Rectangle) and (
            self.size == other.size and
            self.position == other.position
        )

    def render(self, surface, offset):
        pygame.draw.rect(
            surface,
            WHITE,
            (
                int(self.position[0] - offset[0]),
                int(self.position[1] - offset[1]),
                self.size[0],
                self.size[1],
            ),
        )

class Text(Renderable):
    text = None

    # TODO: Should we discard the original text here? These classes _are_
    #       supposed to be immutable.
    def __init__(self, pos, text):
        super(Text, self).__init__(pos)
        self.text = unicode(text)

    def __eq__(self, other):
        return isinstance(other, Rectangle) and (
            self.text == other.text and
            self.position == other.position
        )

    def render(self, surface, offset):
        if (self.position[1] - offset[1]) + DEFAULT_FONT_SIZE < 0:
            return

        # NOTE: We do this in render because it's cheaper to send across a
        #       string and render on each window than to render server-side
        #       and send across the image (I'm actually not even sure if the
        #       image returned by this is serialisable anyway, the only way to
        #       know is to check). We don't need to worry about the cost of
        #       doing this every call to `render` because for this program,
        #       `render` is only called once per instance of this object.
        text_img = default_font().render(
            self.text,
            True,
            WHITE
        )
        surface.blit(
            text_img,
            (
                int(self.position[0] - offset[0]),
                int(self.position[1] - offset[1]),
            ),
        )
