from PIL import ImageDraw
from .. import cell, texture, pzdzi
import re

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

@lru_cache(maxsize=16)
def load_cell_cached(path, cx, cy):
    return cell.load_cell(path, cx, cy)

class TextureRender(object):
    def __init__(self, **options):
        texture_path = options.get('texture')
        cache_name = options.get('cache_name')
        plants_conf = options.get('plants_conf', {})

        self.tl = texture.TextureLibrary(texture_path, cache_name)
        self.tl.config_plants(plants_conf)

class BaseRender(TextureRender):
    def __init__(self, **options):
        self.input = options.get('input')
        TextureRender.__init__(self, **options)

    def square(self, im_getter, ox, oy, sx, sy, layer):
        oy += pzdzi.IsoDZI.SQR_HEIGHT >> 1 # center -> bottom center
        cx, subx = divmod(sx, pzdzi.CELL_SIZE)
        cy, suby = divmod(sy, pzdzi.CELL_SIZE)
        bx, x = divmod(subx, 10)
        by, y = divmod(suby, 10)
        data = load_cell_cached(self.input, cx, cy)
        if not data:
            return
        block = data['blocks'][bx * 30 + by]
        layer_data = block[layer]
        if not layer_data:
            return
        row = layer_data[x]
        if not row:
            return
        square = row[y]
        if not square:
            return
        tiles = data['header']['tiles']
        for t in square['tiles']:
            tex = self.tl.get_by_name(tiles[t])
            if tex:
                tex.render(im_getter.get(), ox, oy)
            else:
                print('missing tile: {}'.format(tiles[t]))

def color_from_sums(color_sums):
    if color_sums:
        r, g, b, n = map(sum, zip(*color_sums))
        color = (r // n, g // n, b // n, 255)
        return color
    return None

def rc_base(tl, tile_names, tile_ids, layer):
    tx = tl.get_by_name(tile_names[tile_ids[0]])
    if tx:
        return color_from_sums([tx.get_color_sum()])
    return None

_half_water = set([
    'blends_natural_02_1',
    'blends_natural_02_2',
    'blends_natural_02_3',
    'blends_natural_02_4',
])
def rc_base_water(tl, tile_names, tile_ids, layer):
    color_sums = []
    for tid in tile_ids:
        name = tile_names[tid]
        tx = tl.get_by_name(name)
        if tx:
            color_sum = tx.get_color_sum()
            if color_sum:
                if len(color_sums) == 0:
                    color_sums.append(color_sum)
                if name in _half_water:
                    color_sums.append(color_sum)
                    break
    return color_from_sums(color_sums)

def rc_avg(tl, tile_names, tile_ids, layer):
    color_sums = []
    for tid in tile_ids:
        name = tile_names[tid]
        tx = tl.get_by_name(name)
        if tx:
            color_sum = tx.get_color_sum()
            if color_sum:
                color_sums.append(color_sum)
    return color_from_sums(color_sums)


_cz_rules0 = [
    [0,    5, (218, 165,  32, 255),      'corn', re.compile('vegetation_farm')],
    [1, None, ( 38,  53,  22, 255),      'tree', re.compile('(_trees|jumbo)')],
    [0,    1, (132,  81,  76, 255),  'tilesand', re.compile('(floors_exterior_tilesandstone|floors_interior_carpet|floors_interior_tilesandwood)')],
    [1, None, ( 73,  58,  43, 255),     'rails', re.compile('_railroad')],
    [1, None, ( 48,  73,  32, 255), 'vegetaion', re.compile('^vegetation')],
    [1,  100, ( 93,  44,  39, 255),     'walls', re.compile('^walls')],
    [0,    1, (108, 127, 131, 255),     'water', re.compile('_natural_(.*_)*0*2_\\d+$')],
    [0,    1, (128, 128, 128, 255),    'street', re.compile('_street_')],
    [0,    1, (217, 207, 183, 255),      'sand', re.compile('_natural_(.*_)*0*1_0*([0-9]|1[0-5])$')],
    [0,    1, ( 75,  88,  27, 255), 'darkgrass', re.compile('_natural_(.*_)*0*1_0*(1[6-9]|2[0-9]|3[0-1])$')],
    [0,    1, ( 97, 103,  36, 255),  'medgrass', re.compile('_natural_(.*_)*0*1_0*(3[2-9]|4[0-7])$')],
    [0,    1, (127, 120,  45, 255), 'litegrass', re.compile('_natural_(.*_)*0*1_0*(4[8-9]|5[0-9]|6[0-3])$')],
    [0,    1, ( 91,  63,  21, 255),      'dirt', re.compile('_natural_(.*_)*0*1_0*(6[4-9]|7[0-9])$')],
    [0,    8, (132,  81,  76, 255),  'tilesand', re.compile('location_')],
]

_cz_rules1 = [
    [1,  100, ( 93,  44,  39, 255),     'walls', re.compile('^walls')],
]

def rc_cartozed(tl, tile_names, tile_ids, layer):
    rules = _cz_rules0 if layer == 0 else _cz_rules1
    for begin, end, color, rname, pattern in rules:
        if end is None or end > len(tile_ids):
            end = len(tile_ids)
        for i in range(begin, end):
            if pattern.search(tile_names[tile_ids[i]]):
                return color
    return None

_top_color_func = {
    'base': rc_base,
    'base+water': rc_base_water,
    'avg': rc_avg,
    'carto-zed': rc_cartozed,
}

class BaseTopRender(TextureRender):
    def __init__(self, **options):
        mode = options.get('top_view_color_mode', 'base+water')
        self.color = _top_color_func[mode]
        self.input = options.get('input')
        TextureRender.__init__(self, **options)

    def tile(self, im_getter, cx, cy, layer, size):
        data = cell.load_cell(self.input, cx, cy)
        tile_names = data['header']['tiles']
        draw = None
        im = None
        if not data:
            return
        for bx in range(30):
            for by in range(30):
                block = data['blocks'][bx * 30 + by]
                if block is None:
                    continue
                layer_data = block[layer]
                if layer_data is None:
                    continue
                for x in range(10):
                    row = layer_data[x]
                    if row is None:
                        continue
                    for y in range(10):
                        square = row[y]
                        if square is None:
                            continue
                        color = self.color(self.tl, tile_names, square['tiles'], layer)
                        if not color:
                            continue
                        if draw is None:
                            im = im_getter.get()
                            if im is None:
                                print(im_getter)
                            draw = ImageDraw.Draw(im)
                        px = (bx * 10 + x) * size
                        py = (by * 10 + y) * size
                        box = [px, py, px + size - 1, py + size - 1]
                        draw.rectangle(box, fill=color)

