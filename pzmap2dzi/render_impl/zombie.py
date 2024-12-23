from PIL import ImageDraw
import os
from .common import render_text, draw_square, LazyFont
from .. import lotheader

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

@lru_cache(maxsize=128)
def load_cell(path, cx, cy):
    header = lotheader.load_lotheader(path, cx, cy)
    if not header:
        return None
    zpop = header['zpop']
    for row in zpop:
        for z in row:
            if z > 0:
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

class ZombieRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.zombie_count = options.get('zombie_count', False)
        font_name = options.get('zombie_count_font')
        if not font_name:
            font_name = options.get('default_font', 'arial.tff')
        font_size = options.get('zombie_count_font_size')
        if not font_size:
            font_size = options.get('default_font_size', 40)
        self.font = LazyFont(font_name, int(font_size))

    def update_options(self, options):
        options['render_layers'] = [0]
        return options

    def valid_cell(self, x, y):
        return load_cell(self.input, x, y) is not None

    def tile(self, im_getter, dzi, gx0, gy0, gl, gr, gt, gb, layer):
        draw = None
        sxmax = (gb + gr) >> 1
        symax = (gb - gl) >> 1
        sxmin = (gt + gl) >> 1
        symin = (gt - gr) >> 1
        for blockx in range(sxmin // dzi.block_size, (sxmax // dzi.block_size) + 1):
            sx = blockx * dzi.block_size
            cx, bx = divmod(blockx, dzi.cell_size_in_block)
            for blocky in range(symin // dzi.block_size, (symax // dzi.block_size) + 1):
                cy, by = divmod(blocky, dzi.cell_size_in_block)
                zpop = load_cell(self.input, cx, cy)
                if not zpop:
                    continue
                zombie = zpop[bx][by]
                if zombie == 0:
                    continue
                color = get_color(zombie, 128)
                sy = blocky * dzi.block_size
                gx = sx - sy
                gy = sx + sy
                ox, oy = dzi.get_sqr_center(gx - gx0, gy - gy0)
                if draw == None:
                    im = im_getter.get()
                    draw = ImageDraw.Draw(im)
                draw_square(draw, ox, oy, color, dzi.block_size)
                gxz = gx + dzi.block_size - 1
                gyz = gy + dzi.block_size - 1
                oxz, oyz = dzi.get_sqr_center(gxz - gx0, gyz - gy0)
                text_color = get_color(zombie, 255)
                t = 'z:{}'.format(zombie)
                render_text(draw, oxz, oyz, t, text_color, self.font.get())

    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        bx, x = divmod(subx, dzi.block_size)
        by, y = divmod(suby, dzi.block_size)
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
            render_text(draw, ox, oy, 'z:{}'.format(zombie), color, self.font.get())

class ZombieTopRender(object):
    def __init__(self, **options):
        self.input = options.get('input')

    def update_options(self, options):
        options['render_layers'] = [0]
        return options

    def tile(self, im_getter, dzi, cx, cy, layer):
        zpop = load_cell(self.input, cx, cy)
        if not zpop:
            return
        
        size = dzi.square_size*dzi.block_size
        im = im_getter.get()
        draw = ImageDraw.Draw(im)
        for bx, row in enumerate(zpop):
            for by, zombie in enumerate(row):
                if zombie == 0:
                    continue
                color = get_color(zombie, 128)
                shape = [bx*size, by*size, (bx + 1)*size, (by + 1)*size]
                draw.rectangle(shape, fill=color)

