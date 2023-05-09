from PIL import ImageDraw
from .. import cell, texture, pzdzi

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
        season = options.get('season', 'summer2')
        snow = options.get('snow', False)
        flower = options.get('flower', False)
        large_bush = options.get('large_bush', False)
        tree_size = options.get('tree_size', 2)
        jumbo_tree_size = options.get('jumbo_tree_size', 3)
        jumbo_tree_type = options.get('jumbo_tree_type', 0)

        self.tl = texture.TextureLibrary(texture_path, True)
        self.tl.config_plants(season, snow, flower, large_bush,
                              tree_size, jumbo_tree_size, jumbo_tree_type)

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

def rc_base(tl, tile_names, tile_ids):
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
def rc_base_water(tl, tile_names, tile_ids):
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

def rc_avg(tl, tile_names, tile_ids):
    color_sums = []
    for tid in tile_ids:
        name = tile_names[tid]
        tx = tl.get_by_name(name)
        if tx:
            color_sum = tx.get_color_sum()
            if color_sum:
                color_sums.append(color_sum)
    return color_from_sums(color_sums)

_top_color_func = {
    'base': rc_base,
    'base+water': rc_base_water,
    'avg': rc_avg,
}

class BaseTopRender(TextureRender):
    def __init__(self, **options):
        mode = options.get('top_color_mode', 'base+water')
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
                        color = self.color(self.tl, tile_names, square['tiles'])
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

