from .. import pzdzi, geometry

def render_text(draw, x, y, text, color, font):
    w, h = draw.textsize(text, font)
    draw.text((x - (w >> 1), y - (h >> 1)), text, color, font)

def draw_square(draw, x, y, color):
    h = pzdzi.IsoDZI.HALF_SQR_HEIGHT
    w = pzdzi.IsoDZI.HALF_SQR_WIDTH
    draw.polygon([x, y - h, x + w, y, x, y + h, x - w, y], fill=color)

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
    w, h = draw.textsize(text, font)
    if w >= pzdzi.IsoDZI.SQR_WIDTH:
        text = break_long_text(text)
        w, h = draw.textsize(text, font)
    #draw.rectangle([x - w // 2, y - h // 2, x + w // 2, y + h // 2], fill=(0, 0, 0, 0))
    draw.text((x - w // 2, y - h // 2), text, color, font, align='center')

_PAD_Y = 5
_PAD_X = 10
def render_edge(draw, x, y, color, width, border_flags):
    edges = geometry.get_edge_segments(border_flags, x, y,
            pzdzi.IsoDZI.HALF_SQR_WIDTH, pzdzi.IsoDZI.HALF_SQR_HEIGHT,
            _PAD_X, _PAD_Y)
    for edge in edges:
        draw.line(edge, fill=color, width=width)
