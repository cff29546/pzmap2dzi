from .. import pzdzi, geometry
import PIL
from PIL import ImageFont
import json
import io


class LazyFont(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.font = None

    def get(self):
        if self.font is None:
            self.font = ImageFont.truetype(self.name, self.size)
        return self.font


if tuple(map(int, PIL.__version__.split('.'))) >= (8, 0, 0):
    def text_size(draw, text, font):
        left, top, right, bottom = draw.textbbox((0, 0), text, font)
        return left, top, right - left, bottom - top
else:
    def text_size(draw, text, font):
        w, h = draw.textsize(text, font)
        return 0, 0, w, h


def render_text(draw, x, y, text, color, font):
    dx, dy, w, h = text_size(draw, text, font)
    draw.text((x - (w >> 1) - dx, y - (h >> 1) - dy),
              text, color, font)


def draw_square(draw, x, y, color, sizew=1, sizeh=1):
    h = pzdzi.IsoDZI.GRID_HEIGHT
    w = pzdzi.IsoDZI.GRID_WIDTH
    path = [
        x                      , y - h                      ,  # top
        x + sizew * w          , y + (sizew - 1) * h        ,  # right
        x + (sizew - sizeh) * w, y + (sizew + sizeh - 1) * h,  # bottom
        x - sizeh * w          , y + (sizeh - 1) * h        ,  # left
    ]
    draw.polygon(path, fill=color)


SUFFIX = [
    'store',
    'storage',
    'kitchen',
    'bathroom',
    'room',
    'rooms',
    'factory',
    'occupied',
    'dining',
    'warehouse',
    'restaurant',
    'clothes',
    'station',
    'game',
    'stand',
    'shipping',
    'cooking',
    'office',
    'print',
    'bottling',
]
def break_long_text(text):
    for s in SUFFIX:
        if text.endswith(s):
            return text[:len(text) - len(s)] + '\n' + s
    l = len(text) // 2
    return text[:l] + '\n' + text[l:]


def render_long_text(draw, x, y, text, color, font):
    dx, dy, w, h = text_size(draw, text, font)
    if w >= pzdzi.IsoDZI.SQUARE_WIDTH:
        text = break_long_text(text)
        dx, dy, w, h = text_size(draw, text, font)
    draw.text((x - dx - w // 2, y - dy - h // 2),
              text, color, font, align='center')


_PAD_Y = 5
_PAD_X = 10
def render_edge(draw, x, y, color, width, border_flags):
    edges = geometry.get_edge_segments(border_flags, x, y,
                                       pzdzi.IsoDZI.GRID_WIDTH,
                                       pzdzi.IsoDZI.GRID_HEIGHT,
                                       _PAD_X, _PAD_Y)
    for edge in edges:
        draw.line(edge, fill=color, width=width)


def dump_marks(marks, output_path, compact=False):
    with io.open(output_path, 'w', encoding='utf-8') as f:
        start = True
        f.write('[\n')
        for mark in marks:
            if not start:
                f.write(',')
            else:
                start = False
            if compact:
                mark = compact_mark(mark)
            f.write(json.dumps(mark, separators=(',', ':')))
            f.write('\n')
        f.write(']')

def compact_mark(mark):
    rects = []
    for rect in mark.get('rects', []):
        rects.append('{},{},{},{}'.format(
            rect['x'],
            rect['y'],
            rect['width'],
            rect['height'],
        ))
    return '{}:{}:{}:{}'.format(
        mark['name'],
        mark['layer'],
        mark['color'],
        ':'.join(rects),
    )
