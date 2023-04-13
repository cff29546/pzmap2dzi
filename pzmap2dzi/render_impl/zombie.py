from PIL import ImageDraw, ImageFont
import os
from .common import render_text, draw_square
from .. import lotheader, pzdzi

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

@lru_cache(maxsize=128)
def load_cell(path, cx, cy):
    name = os.path.join(path, '{}_{}.lotheader'.format(cx, cy))
    if not os.path.isfile(name):
        return None
    header = lotheader.load_lotheader(name)
    zpop = header['zpop']
    for i in range(30):
        for j in range(30):
            if zpop[i][j] > 0:
                return zpop
    return None

def get_color(zombie, alpha):
    r = g = b = 0
    if zombie >= 128:
        r = (zombie - 128) << 1
        g = 255 - r
    else:
        g = zombie << 1
        b = 255 - g
    return (r, g, b, alpha)

ZOMBIE_FONT = ImageFont.truetype("arial.ttf", 40)

class ZombieRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.zombie_count = options.get('zombie_count', False)

    def update_options(self, options):
        options['layers'] = 1
        return options

    def valid_cell(self, x, y):
        return load_cell(self.input, x, y) is not None

    def tile(self, im_getter, gx0, gy0, gl, gr, gt, gb, layer):
        drawing = []
        text = []
        for gy in range(gt, gb + 1):
            for gx in range(gl, gr + 1):
                if (gx + gy) & 1:
                    continue
                sx = (gx + gy) >> 1
                sy = (gy - gx) >> 1
                cx, subx = divmod(sx, pzdzi.CELL_SIZE)
                cy, suby = divmod(sy, pzdzi.CELL_SIZE)
                zpop = load_cell(self.input, cx, cy)
                if not zpop:
                    continue
                bx, x = divmod(subx, 10)
                by, y = divmod(suby, 10)
                zombie = zpop[bx][by]
                if zombie == 0:
                    continue
                ox, oy = pzdzi.IsoDZI.get_sqr_center(gx - gx0, gy - gy0)
                color = get_color(zombie, 128)
                drawing.append((draw_square, (ox, oy, color)))
                if self.zombie_count and x == 9 and y == 0:
                    color = get_color(zombie, 255)
                    t = 'z:{}'.format(zombie)
                    text.append((render_text, (ox, oy, t, color, ZOMBIE_FONT)))

        if drawing or text:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            for func, args in drawing:
                func(draw, *args)
            for func, args in text:
                func(draw, *args)

    def square(self, im_getter, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, pzdzi.CELL_SIZE)
        cy, suby = divmod(sy, pzdzi.CELL_SIZE)
        bx, x = divmod(subx, 10)
        by, y = divmod(suby, 10)
        zpop = load_cell(self.input, cx, cy)
        if not zpop:
            return
        zombie = zpop[bx][by]
        if zombie == 0:
            return
        im = im_getter.get()
        draw = ImageDraw.Draw(im)
        color = get_color(zombie, 128)
        draw_square(draw, ox, oy, color)
        if self.zombie_count and x == 9 and y == 0:
            color = get_color(zombie, 255)
            render_text(draw, ox, oy, str(zombie), color, ZOMBIE_FONT)

class ZombieTopRender(object):
    def __init__(self, **options):
        self.input = options.get('input')

    def update_options(self, options):
        options['layers'] = 1
        return options

    def tile(self, im_getter, cx, cy, layer, size):
        zpop = load_cell(self.input, cx, cy)
        if not zpop:
            return

        im = None
        draw = None
        for bx in range(30):
            for by in range(30):
                zombie = zpop[bx][by]
                if zombie == 0:
                    continue
                if draw is None:
                    im = im_getter.get()
                    draw = ImageDraw.Draw(im)
                color = get_color(zombie, 128)
                shape = [bx * 10 * size, by * 10 * size,
                         (bx + 1) * 10 * size, (by + 1) * 10 * size]
                draw.rectangle(shape, fill=color)

