import os
from .common import render_text, draw_square, LazyFont, dump_marks
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


def to_css_color(rgba):
    r, g, b, a = rgba
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)


class ZombieMark(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.output = options.get('output')

    def process(self, dzi):
        marks = []
        block_size = dzi.block_size
        for cx, cy in dzi.cells:
            zpop = load_cell(self.input, cx, cy)
            if not zpop:
                continue
            dx = cx * dzi.cell_size
            dy = cy * dzi.cell_size
            for bx, row in enumerate(zpop):
                sx = dx + bx * block_size
                for by, zombie in enumerate(row):
                    if zombie == 0:
                        continue
                    sy = dy + by * block_size
                    text = str(zombie)
                    text_color = to_css_color(get_color(zombie, 255))
                    marks.append({
                        'type': 'text',
                        'x': sx + block_size // 2,
                        'y': sy + block_size // 2,
                        'name': text,
                        'color': text_color,
                    })

        print('  zombie marks: {}'.format(len(marks)))
        if marks:
            output_path = os.path.join(self.output, 'marks.json')
            dump_marks(marks, output_path)
        return True


class ZombieRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.zombie_count = options.get('zombie_count', False)
        self.use_mark = options.get('use_mark')
        if self.use_mark:
            self.mark = ZombieMark(**options)

        font_name = options.get('zombie_count_font')
        if not font_name:
            font_name = options.get('default_font', 'arial.tff')
        font_size = options.get('zombie_count_font_size')
        if not font_size:
            font_size = options.get('default_font_size', 40)
        self.font = LazyFont(font_name, int(font_size))

    def render(self, dzi):
        if self.zombie_count and self.use_mark:
            return self.mark.process(dzi)
        return True

    def update_options(self, options):
        options['render_minlayer'] = 0
        options['render_maxlayer'] = 1
        options['render_margin'] = None
        return options

    def valid_cell(self, x, y):
        return load_cell(self.input, x, y) is not None

    def tile(self, im_getter, dzi, gx0, gy0, layer):
        draw = None
        block_size = dzi.block_size
        gx1 = gx0 + dzi.grid_per_tilex
        gy1 = gy0 + dzi.grid_per_tiley
        sxmax = (gy1 + gx1) >> 1
        symax = (gy1 - gx0) >> 1
        sxmin = (gy0 + gx0) >> 1
        symin = (gy0 - gx1) >> 1
        blockxmax = sxmax // block_size + 1
        blockymax = symax // block_size + 1
        blockxmin = sxmin // block_size
        blockymin = symin // block_size
        for blockx in range(blockxmin, blockxmax):
            sx = blockx * block_size
            cx, bx = divmod(blockx, dzi.cell_size_in_block)
            for blocky in range(blockymin, blockymax):
                cy, by = divmod(blocky, dzi.cell_size_in_block)
                zpop = load_cell(self.input, cx, cy)
                if not zpop:
                    continue
                zombie = zpop[bx][by]
                if zombie == 0:
                    continue
                color = get_color(zombie, 128)
                sy = blocky * block_size
                gx = sx - sy
                gy = sx + sy
                ox, oy = dzi.get_sqr_center(gx - gx0, gy - gy0)
                if draw is None:
                    draw = im_getter.get_draw()
                draw_square(draw, ox, oy, color, block_size, block_size)
                gxz = gx + block_size - 1
                gyz = gy + block_size - 1
                oxz, oyz = dzi.get_sqr_center(gxz - gx0, gyz - gy0)
                if self.zombie_count and not self.use_mark:
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
        draw = im_getter.get_draw()
        color = get_color(zombie, 128)
        draw_square(draw, ox, oy, color)
        if self.zombie_count and not self.use_mark and x == 9 and y == 0:
            color = get_color(zombie, 255)
            t = 'z:{}'.format(zombie)
            render_text(draw, ox, oy, t, color, self.font.get())


class ZombieTopRender(object):
    def __init__(self, **options):
        self.input = options.get('input')

    def update_options(self, options):
        options['render_minlayer'] = 0
        options['render_maxlayer'] = 1
        return options

    def tile(self, im_getter, dzi, cx, cy, layer):
        zpop = load_cell(self.input, cx, cy)
        if not zpop:
            return
        size = dzi.square_size*dzi.block_size
        draw = im_getter.get_draw()
        for bx, row in enumerate(zpop):
            for by, zombie in enumerate(row):
                if zombie == 0:
                    continue
                color = get_color(zombie, 128)
                x, y = bx * size, by * size
                shape = [x, y, x + size - 1, y + size - 1]
                draw.rectangle(shape, fill=color)
