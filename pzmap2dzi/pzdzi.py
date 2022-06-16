from PIL import Image
import os
from . import util, mp

LAYER_HEIGHT = 192
SQR_HEIGHT = 64
SQR_WIDTH = 128
CELL_SIZE = 300

def get_offset_in_tile(gx, gy):
    ox = (gx - 1) * SQR_WIDTH // 2
    oy = (gy - 7) * SQR_HEIGHT // 2
    return ox, oy

def load_tile(path, tx, ty, ext):
    tile = os.path.join(path, '{}_{}.{}'.format(tx, ty, ext))
    if os.path.isfile(tile):
        return Image.open(tile)
    return None

class DZI(object):
    def __init__(self, tile_size, w, h, layers):
        self.w = w
        self.h = h
        self.tile_size = tile_size
        self.layers = layers
        self.build_pyramid()

    def build_pyramid(self):
        self.pyramid = [(self.w, self.h)]
        while self.pyramid[-1] != (1, 1):
            x, y = self.pyramid[-1]
            x, y = (x + 1) // 2, (y + 1) // 2
            self.pyramid.append((x, y))
        self.pyramid.reverse()
        self.base_level = len(self.pyramid) - 1

    def tile2coord(self, tx, ty):
        return tx * self.tile_size, ty * self.tile_size

    def crop_tile(self, im, tx, ty, level=None):
        if level is None:
            level = self.base_level
        x, y = self.tile2coord(tx + 1, ty + 1)
        w, h = self.pyramid[level]
        if x <= w and y <= h:
            return im
        w = self.tile_size - max(0, x - w)
        h = self.tile_size - max(0, y - h)
        return im.crop((0, 0, w, h))

    def ensure_folders(self, path, layers=None):
        if layers is None:
            layers = self.layers
        for layer in range(layers):
            for level in range(len(self.pyramid)):
                util.ensure_folder(os.path.join(path, 'layer{}_files'.format(layer), str(level)))

    def save_dzi(self, path, ext, layers=None):
        util.ensure_folder(path)
        dzi = '''<?xml version="1.0" encoding="UTF-8"?>
        <Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="{}" Overlap="0" Format="{}">
                <Size Width="{}" Height="{}"/>
        </Image>'''.format(self.tile_size, ext, self.w, self.h)
        if layers is None:
            layers = self.layers
        for layer in range(layers):
            with open(os.path.join(path, 'layer{}.dzi'.format(layer)), 'w') as f:
                f.write(dzi)

    def merge_tile(self, path, tx, ty, level, ext):
        in_path = os.path.join(path, str(level + 1))
        out_path = os.path.join(path, str(level))
        util.set_wip(out_path, tx, ty)
        mode = 'RGBA'
        if ext == 'jpg':
            mode = 'RGB'
        tile = Image.new(mode, (self.tile_size * 2, self.tile_size * 2))
        for i, j in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            ntx = tx * 2 + i
            nty = ty * 2 + j
            ntile = load_tile(in_path, ntx, nty, ext)
            if ntile:
                tile.paste(ntile, (self.tile_size * i, self.tile_size * j))
        tile.thumbnail((self.tile_size, self.tile_size), Image.ANTIALIAS)
        tile = self.crop_tile(tile, tx, ty, level)
        tile.save(os.path.join(out_path, '{}_{}.{}'.format(tx, ty, ext)))
        util.clear_wip(out_path, tx, ty)

    def _merge_work(self, conf, tx_ty):
        tx, ty = tx_ty
        path, level, ext = conf
        self.merge_tile(path, tx, ty, level, ext)

    def get_level_tiles(self, path, ext, level):
        in_path = os.path.join(path, str(level + 1))
        out_path = os.path.join(path, str(level))
        done = util.get_done_tiles(out_path, ext)
        tiles = set()
        for f in os.listdir(in_path):
            m = util.TILE_PATTERN[ext].match(f)
            if m:
                x, y = map(int, m.groups())
                x = x // 2
                y = y // 2
                if (x, y) not in done:
                    tiles.add((x, y))
        return list(tiles)

    def merge_level(self, path, level, ext, parallel=1, verbose=False, stop_key=None):
        conf = (path, level, ext)
        t = mp.Task(self._merge_work, conf, parallel)
        return t.run(self.get_level_tiles(path, ext, level), verbose, stop_key)

    def merge_all_levels(self, path, ext, parallel=1, verbose=False, stop_key=None):
        for level in reversed(range(self.base_level)):
            if verbose:
                print('processing level {}:'.format(level))
            if not self.merge_level(path, level, ext, parallel, verbose, stop_key):
                return False
        return True

class IsoDZI(DZI):
    def __init__(self, map_path, tile_size, layers, use_jumbo_tree):
        self.layers = layers
        self.use_jumbo_tree = True
        self.cells = set(util.get_all_cells(map_path))

        assert tile_size % SQR_WIDTH == 0
        assert tile_size % SQR_HEIGHT == 0
        assert len(self.cells) > 0
        gxmin = None
        gxmax = None
        gymin = None
        gymax = None
        for cx, cy in self.cells:
            left, right, top, bottom = self.cell_grid_bound(cx, cy)
            if gxmin is None:
                gxmin = left
                gxmax = right
                gymin = top
                gymax = bottom
            else:
                gxmin = min(left, gxmin)
                gxmax = max(right, gxmax)
                gymin = min(top, gymin)
                gymax = max(bottom, gymax)

        gxmin -= 2
        gxmax += 2
        gymin -= 2
        gymax += 2

        # grid offset
        self.gxo = gxmin
        self.gyo = gymin
        self.gw = gxmax - gxmin + 1
        self.gh = gymax - gymin + 1
        w = self.gw * SQR_WIDTH // 2
        h = self.gh * SQR_HEIGHT // 2
        self.tile_gw = tile_size * 2 // SQR_WIDTH
        self.tile_gh = tile_size * 2 // SQR_HEIGHT
        self.use_jumbo_tree = use_jumbo_tree
        DZI.__init__(self, tile_size, w, h, layers)

    def tile2grid(self, tx, ty, layer):
        gx = self.gxo + (self.tile_size * 2 // SQR_WIDTH) * tx
        gy = self.gyo + (self.tile_size * 2 // SQR_HEIGHT) * ty + layer * 6
        return gx, gy

    def tile_grid_bound(self, tx, ty, layer):
        left, top = self.tile2grid(tx, ty, layer)
        right, bottom = self.tile2grid(tx + 1, ty + 1, layer)
        if self.use_jumbo_tree:
            return (left - 2, right + 2, top, bottom + 14)
        else:
            return (left, right, top, bottom + 6)

    def square_grid_bound(self, sx1, sy1, sx2, sy2):
        top = sx1 + sy1
        bottom = sx2 + sy2
        left = sx1 - sy2
        right = sx2 - sy1
        return top, bottom, left, right

    def cell_grid_bound(self, cx, cy):
        sx = cx * CELL_SIZE
        sy = cy * CELL_SIZE
        top, bottom, left, right = self.square_grid_bound(sx, sy, sx + CELL_SIZE - 1, sy + CELL_SIZE - 1)
        if self.use_jumbo_tree:
            return (left - 2, right + 2, top - max(14, 6*self.layers), bottom)
        else:
            return (left, right, top - 6*self.layers, bottom)

    def cell2tiles(self, cx, cy):
        left, right, top, bottom = self.cell_grid_bound(cx, cy)
        txmin = (left - self.gxo - 1) // self.tile_gw
        txmax = (right - self.gxo) // self.tile_gw
        tymin = (top - self.gyo - 1) // self.tile_gh
        tymax = (bottom - self.gyo) // self.tile_gh
        tiles = [(tx, ty) for ty in range(tymin, tymax + 1) for tx in range(txmin, txmax + 1)]
        return tiles

    def get_tile_groups(self, out_path, ext, max_group_size=0, skip_cells=set()):
        done = util.get_done_tiles(out_path, ext)
        groups = []
        for cx, cy in sorted(list(self.cells)):
            if (cx, cy) in skip_cells:
                continue
            tiles = self.cell2tiles(cx, cy)
            group = []
            for t in tiles:
                if t not in done:
                    group.append(t)
                    done.add(t)
                    if max_group_size and len(group) == max_group_size:
                        groups.append(group)
                        group = []
            if group:
                groups.append(group)
        return groups

class TopDZI(DZI):
    def __init__(self, map_path, square_size, layers=1):
        self.cells = set(util.get_all_cells(map_path))

        cxmax, cymax = map(max, zip(*self.cells))            
        cxmin, cymin = map(min, zip(*self.cells))            

        self.cxo = cxmin
        self.cyo = cymin
        self.cw = cxmax - cxmin + 1
        self.ch = cymax - cymin + 1
        tile_size = square_size * CELL_SIZE
        w = tile_size * self.cw
        h = tile_size * self.ch
        DZI.__init__(self, tile_size, w, h, layers)

    def tile2cell(self, tx, ty):
        return (tx + self.cxo, ty + self.cyo)

    def cell2tile(self, cx, cy):
        return (cx - self.cxo, cy - self.cyo)

    def get_tiles(self, out_path, ext, skip_cells=set()):
        done = util.get_done_tiles(out_path, ext)
        tiles = []
        for cx, cy in self.cells:
            if (cx, cy) in skip_cells:
                continue
            tile = self.cell2tile(cx, cy)
            if tile not in done:
                tiles.append(tile)
                done.add(tile)
        return tiles
