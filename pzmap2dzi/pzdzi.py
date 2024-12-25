from PIL import Image
import os
import sys
import re
import json
from . import util, mptask, scheduling, geometry, lotheader

DZI_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="{}" Overlap="0" Format="{}">
  <Size Width="{}" Height="{}"/>
</Image>'''

PENDING_PATTERN = re.compile('(\\d+)_(\\d+)\\.pending$')

def lower_level_depend(tx, ty):
    return [(i + (tx << 1), j + (ty << 1))
            for i in (0, 1) for j in (0, 1)]

def get_merge_task_depend(done, lower_task, lower_done):
    tasks = {}
    skip = set()
    for tx, ty in lower_done:
        x = tx >> 1
        y = ty >> 1
        if (x, y) not in done:
            tasks[(x, y)] = 0
    for tx, ty in lower_task:
        x = tx >> 1
        y = ty >> 1
        # in case lower level is skipped
        if (x, y) not in done:
            tasks[(x, y)] = tasks.get((x, y), 0) + 1
        else:
            skip.add((tx,ty))
    return tasks, skip

class DZI(object):
    def __init__(self, w, h, **options):
        self.w = w
        self.h = h
        self.path = options.get('output', './dzi')
        assert self.tile_size != None
        self.save_empty = options.get('save_empty_tile', False)
        self.ext = options.get('image_fmt', 'png')
        self.ext0 = options.get('image_fmt_layer0')
        if not self.ext0:
            self.ext0 = self.ext
        self.save_options = {}
        self.save_options[self.ext] = options.get('image_save_options',{}).get(self.ext, {})
        self.save_options[self.ext0] = options.get('image_save_options',{}).get(self.ext0, {})
        self.done_pattern = re.compile('(\\d+)_(\\d+)\\.(?:empty|{})$'.format(self.ext0))
        self.skip_level = options.get('skip_level', 0)
        self.skip_cells = set()
        self.cache_enabled = False
        self.cache_limit = 0
        if sys.version_info >= (3,8):
            if options.get('enable_cache', True):
                self.cache_enabled = True
                self.cache_limit = options.get('cache_limit_mb', 0)
        self.build_pyramid()

    def build_pyramid(self):
        self.pyramid = [(self.w, self.h)]
        while self.pyramid[-1] != (1, 1):
            x, y = self.pyramid[-1]
            x, y = (x + 1) // 2, (y + 1) // 2
            self.pyramid.append((x, y))
        self.pyramid.reverse()
        self.levels = len(self.pyramid)

    def tile2coord(self, tx, ty):
        return tx * self.tile_size, ty * self.tile_size

    def _crop_tile(self, im, level, tx, ty):
        x, y = self.tile2coord(tx + 1, ty + 1)
        w, h = self.pyramid[level]
        if x <= w and y <= h:
            return im
        w = self.tile_size - max(0, x - w)
        h = self.tile_size - max(0, y - h)
        return im.crop((0, 0, w, h))

    def mark_empty(self, level, tx, ty, layer):
        if self.save_empty:
            ext, path = self.tile_path(level, tx, ty, layer, 'empty')
            with open(path, 'w') as f:
                pass

    def save_tile(self, im, level, tx, ty, layer, force=False):
        write_all = force or not self.cache_enabled
        if not write_all and level >= self.levels - self.skip_level:
            return 'skip'
        if im:
            im = self._crop_tile(im, level, tx, ty)
        if im and im.getbbox():
            ext, path = self.tile_path(level, tx, ty, layer)
        else:
            self.mark_empty(level, tx, ty, layer)
            return 'empty'

        if ext == 'jpg':
           im = im.convert('RGB')

        im.save(path, **self.save_options[ext])

        if (write_all and level != self.levels and
            level + 1 >= self.levels - self.skip_level):
            self.delete_skip_tiles(level, tx, ty, layer)

        return 'saved'

    def delete_skip_tiles(self, level, tx, ty, layer):
        for i in [0, 1]:
            for j in [0, 1]:
                self.delete_tile(level + 1, i + tx*2, j + ty*2, layer)

    def delete_tile(self, level, tx, ty, layer):
        ext, path = self.tile_path(level, tx, ty, layer)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except:
                pass

    def tile_path(self, level, tx, ty, layer, ext=None):
        if ext is None:
            ext = self.ext0 if layer == 0 else self.ext
        path = os.path.join(self.path,
                           'layer{}_files'.format(layer),
                           str(level),
                           '{}_{}.{}'.format(tx, ty, ext))
        return ext, path

    def load_tile(self, level, tx, ty, layer):
        ext, path = self.tile_path(level, tx, ty, layer)
        im = None
        if os.path.isfile(path):
            im = Image.open(path)
            if ext == 'jpg':
                im = im.convert('RGBA')
        return im

    def set_wip(self, level, x, y):
        ext, path = self.tile_path(level, x, y, 0, 'pending')
        with open(path, 'w') as f:
            pass

    def clear_wip(self, level, x, y):
        ext, path = self.tile_path(level, x, y, 0, 'pending')
        os.remove(path)
 
    def create_empty_output(self):
        util.ensure_folder(self.path)
        for layer in self.render_layers:
            layer_path = os.path.join(self.path, 'layer{}_files'.format(layer))
            util.ensure_folder(layer_path)
            for level in range(self.levels):
                util.ensure_folder(os.path.join(layer_path, str(level)))
            ext = self.ext0 if layer == 0 else self.ext
            w, h = self.pyramid[-1 - self.skip_level]
            dzi = DZI_TEMPLATE.format(self.tile_size, ext, w, h)
            dzi_path = os.path.join(self.path, 'layer{}.dzi'.format(layer))
            with open(dzi_path, 'w') as f:
                f.write(dzi)
        self.save_map_info()

    def save_map_info(self):
        w, h = self.pyramid[-1 - self.skip_level]
        info = {
            'w': w,
            'h': h,
            'skip': self.skip_level,
            'cell_rects': geometry.rect_cover(self.cells),
        }
        if hasattr(self, 'update_map_info'):
            info = self.update_map_info(info)
        path = os.path.join(self.path, 'map_info.json')

        data = json.dumps(info, indent=1)
        data = data.replace('\n  ', '').replace('\n ]', ']').replace('[ ', '[')
        with open(path, 'w') as f:
            f.write(data)



    def get_bottom_task_depend(self, skip_cells, done):
        tasks = {}
        for cx, cy in self.cells:
            if (cx, cy) not in skip_cells:
                for t in self.cell2tiles(cx, cy):
                    if t not in done:
                        tasks[t] = 0
        return tasks

    def get_done_tasks(self, level):
        path = os.path.join(self.path, 'layer0_files', str(level))
        if not os.path.isdir(path):
            return set()
        done = set()
        pending = set()
        for f in os.listdir(path):
            m = self.done_pattern.match(f)
            if m:
                x, y = map(int, m.groups())
                done.add((x, y))
                continue
            m = PENDING_PATTERN.match(f)
            if m:
                x, y = map(int, m.groups())
                pending.add((x, y))
        return done - pending  

    def get_tasks(self, skip_cells=set()):
        level_tasks = [None for i in range(self.levels)]
        level_done = [None for i in range(self.levels)]
        level_skip = [set() for i in range(self.levels)]
        for level in reversed(range(self.levels)):
            done = self.get_done_tasks(level)
            if level == self.levels - 1:
                task = self.get_bottom_task_depend(skip_cells, done)
            else:
                task, skip = get_merge_task_depend(done, level_tasks[level+1], level_done[level+1])
                level_skip[level + 1] = skip
            level_tasks[level] = task
            level_done[level] = done

        # skip tasks from high level done
        for level in range(1, self.levels):
            for t in level_skip[level - 1]:
                for lt in lower_level_depend(*t):
                    if lt in level_tasks[level]:
                        level_skip[level].add(lt)
            for t in level_skip[level]:
                level_done[level].add(t)
                del level_tasks[level][t]

        return level_tasks, level_done

    def merge_tile(self, im_getter, level, tx, ty, layer, cached=None):
        tile = None
        for i in [0, 1]:
            for j in [0, 1]:
                idx = j + i*2
                if cached and cached[idx] is not None:
                    im = cached[idx]
                else:
                    im = self.load_tile(level + 1, i + tx*2, j + ty*2, layer)
                if im == 'empty':
                    im = None
                if im:
                    if not tile:
                        tile = Image.new('RGBA', (self.tile_size*2, self.tile_size*2))
                    tile.paste(im, (self.tile_size * i, self.tile_size * j))
                    im = None
        if tile:
            tile.thumbnail((self.tile_size, self.tile_size), Image.LANCZOS)
            im_getter.get().paste(tile, (0, 0))

    def render_all(self, render, n, break_key=None, verbose=False, profile=False):
        if verbose:
            print('Preparing data')
        self.create_empty_output()
        if hasattr(render, 'valid_cell'):
            for x, y in self.cells:
                if not render.valid_cell(x, y):
                    self.skip_cells.add((x, y))
        tasks, done = self.get_tasks(self.skip_cells)
        schd = scheduling.TopologicalDziScheduler(self, break_key, verbose)
        cache_prefix = 'pzdzi.{}.'.format(os.getpid())
        worker = scheduling.TopologicalDziWorker(self, cache_prefix, render)
        task = mptask.Task(worker, schd, profile)
        task.run((tasks, done), n)
        if schd.stop:
            if verbose:
                print('Render interrupted: {}'.format(schd.stop))
            return False
        if verbose:
            print('Done')
        return True

PZ_VERSION_NAME = {
    0: 'B41',
    1: 'B42',
}
class PZDZI(DZI):
    def pz_init(self, path, **options):
        version_info = lotheader.get_version_info(path)
        self.pz_version = PZ_VERSION_NAME.get(version_info['version'], 'Unknown')
        self.cells = version_info['cells']
        self.cell_size_in_block = version_info['cell_size_in_block']
        self.block_size = version_info['block_size']
        self.cell_size = version_info['cell_size']
        self.minlayer = version_info['minlayer']
        self.maxlayer = version_info['maxlayer']
        layer_range = options.get('layer_range', 'all')
        if layer_range != 'all':
            self.minlayer = max(self.minlayer, layer_range[0])
            self.maxlayer = min(self.maxlayer, layer_range[1])
        if self.minlayer > 0:
            self.minlayer = 0
        if self.maxlayer < 1:
            self.maxlayer = 1
        self.render_layers = list(range(self.minlayer, 0)) + list(reversed(range(self.maxlayer)))
        render_layers = options.get('render_layers', None)
        if render_layers is not None:
            self.render_layers = render_layers
        self.layers = max(self.render_layers) - min(self.render_layers) + 1
        if options.get('verbose'):
            print('PZ version: {} , layer range [{}, {})'.format(
                  self.pz_version, self.minlayer, self.maxlayer))

    def update_pz_map_info(self, info):
        info['cell_size'] = self.cell_size
        info['block_size'] = self.block_size
        info['pz_version'] = self.pz_version
        info['maxlayer'] = self.maxlayer
        info['minlayer'] = self.minlayer
        return info

class IsoDZI(PZDZI):
    SQR_HEIGHT = 64
    HALF_SQR_HEIGHT = SQR_HEIGHT >> 1
    SQR_WIDTH = 128
    HALF_SQR_WIDTH = SQR_WIDTH >> 1
    # normal texture size      w:128 h:256
    # jumbo tree texutre size  w:384 h:512
    def get_sqr_center(self, gx, gy):
        ox = gx * IsoDZI.HALF_SQR_WIDTH
        oy = gy * IsoDZI.HALF_SQR_HEIGHT
        return ox, oy

    def __init__(self, map_path, **options):
        self.pz_init(map_path, **options)
        self.sqr_height = IsoDZI.SQR_HEIGHT
        self.sqr_width = IsoDZI.SQR_WIDTH
        self.tile_size = options.get('tile_size', 1024)

        assert self.tile_size % self.sqr_width == 0
        assert self.tile_size % self.sqr_height == 0
        assert len(self.cells) > 0
        gxmin = None
        gxmax = None
        gymin = None
        gymax = None
        self.use_jumbo_tree = True
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
        w = self.gw * IsoDZI.HALF_SQR_WIDTH
        h = self.gh * IsoDZI.HALF_SQR_HEIGHT
        self.tile_gw = self.tile_size // IsoDZI.HALF_SQR_WIDTH
        self.tile_gh = self.tile_size // IsoDZI.HALF_SQR_HEIGHT
        self.use_jumbo_tree = options.get('jumbo_tree_size', 3) > 3
        DZI.__init__(self, w, h, **options)

    def tile2grid(self, tx, ty, layer):
        gx = self.gxo + (self.tile_size // IsoDZI.HALF_SQR_WIDTH) * tx
        gy = self.gyo + (self.tile_size // IsoDZI.HALF_SQR_HEIGHT) * ty + layer * 6
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
        sx = cx * self.cell_size
        sy = cy * self.cell_size
        top, bottom, left, right = self.square_grid_bound(sx, sy, sx + self.cell_size - 1, sy + self.cell_size - 1)
        if self.use_jumbo_tree:
            return (left - 2, right + 2, top - max(14, 6*self.maxlayer), bottom - 6*self.minlayer)
        else:
            return (left, right, top - 6*self.maxlayer, bottom - 6*self.minlayer)

    def cell2tiles(self, cx, cy):
        left, right, top, bottom = self.cell_grid_bound(cx, cy)
        txmin = (left - self.gxo - 1) // self.tile_gw
        txmax = (right - self.gxo) // self.tile_gw
        tymin = (top - self.gyo - 1) // self.tile_gh
        tymax = (bottom - self.gyo) // self.tile_gh
        tiles = [(tx, ty) for ty in range(tymin, tymax + 1) for tx in range(txmin, txmax + 1)]
        return tiles

    def render_tile(self, im_getter, render, tx, ty, layer):
        gx0, gy0 = self.tile2grid(tx, ty, layer)
        left, right, top, bottom = self.tile_grid_bound(tx, ty, layer)
        if hasattr(render, 'tile'):
            return render.tile(im_getter, self, gx0, gy0, left, right, top, bottom, layer)
        for gy in range(top, bottom + 1):
            for gx in range(left, right + 1):
                if (gx + gy) & 1:
                    continue
                sx = (gx + gy) >> 1
                sy = (gy - gx) >> 1
                ox, oy = self.get_sqr_center(gx - gx0, gy - gy0)
                render.square(im_getter, self, ox, oy, sx, sy, layer)

    def update_map_info(self, info):
        info = self.update_pz_map_info(info)
        info['x0'] = -self.gxo * IsoDZI.HALF_SQR_WIDTH
        info['y0'] = -(self.gyo + 1) * IsoDZI.HALF_SQR_HEIGHT
        info['sqr'] = 2 * IsoDZI.HALF_SQR_WIDTH
        return info

class TopDZI(PZDZI):
    def __init__(self, map_path, **options):
        self.pz_init(map_path, **options)
        self.square_size = options.get('top_view_square_size', 1)

        cxmax, cymax = map(max, zip(*self.cells))            
        cxmin, cymin = map(min, zip(*self.cells))            

        self.cxo = cxmin
        self.cyo = cymin
        self.cw = cxmax - cxmin + 1
        self.ch = cymax - cymin + 1
        self.tile_size = self.square_size * self.cell_size
        w = self.tile_size * self.cw
        h = self.tile_size * self.ch
        DZI.__init__(self, w, h, **options)

    def tile2cell(self, tx, ty):
        return (tx + self.cxo, ty + self.cyo)

    def cell2tiles(self, cx, cy):
        return [(cx - self.cxo, cy - self.cyo)]

    def render_tile(self, im_getter, render, tx, ty, layer):
        cx, cy = self.tile2cell(tx, ty)
        render.tile(im_getter, self, cx, cy, layer)

    def update_map_info(self, info):
        info = self.update_pz_map_info(info)
        info['x0'] = -(self.cxo * self.square_size * self.cell_size)
        info['y0'] = -(self.cyo * self.square_size * self.cell_size)
        info['sqr'] = self.square_size
        return info
