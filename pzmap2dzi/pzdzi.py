from PIL import Image
import os
import sys
import re
import time
import datetime
from . import util, mptask, scheduling, geometry, lotheader, source_manager

DZI_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="{tile_size}" Overlap="0" Format="{format}">
  <Size Width="{width}" Height="{height}"/>
</Image>
'''
PENDING_PATTERN = re.compile('(\\d+)_(\\d+)\\.pending$')
DONE_TEMPLATE = '(\\d+)_(\\d+)\\.(?:empty|{})$'


RGB_FMT = set(['jpg', 'jpeg'])


def supports_RGBA(ext):
    if ext in RGB_FMT:
        return False
    return True


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
            skip.add((tx, ty))
    return tasks, skip


def align_origin(origin, align):
    align = int(align)
    if align == 0:
        return origin
    return align * (origin // align)


class DZI(object):
    def __init__(self, w, h, **options):
        self.w = w
        self.h = h
        self.path = options.get('output', './dzi')
        assert self.tile_size is not None
        self.save_empty = options.get('save_empty_tile', False)
        self.ext = options.get('image_fmt', 'png').lower()
        self.ext0 = options.get('image_fmt_layer0', self.ext).lower()
        self.save_options = {}
        self.save_options[self.ext] = {}
        self.save_options[self.ext0] = {}
        save_options = options.get('image_save_options', {})
        if save_options:
            self.save_options[self.ext] = save_options.get(self.ext, {})
            self.save_options[self.ext0] = save_options.get(self.ext0, {})
        self.done_pattern = re.compile(DONE_TEMPLATE.format(self.ext0))
        self.skip_level = options.get('skip_level', 0)
        self.cache_enabled = False
        self.cache_limit = 0
        if sys.version_info >= (3, 8):
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
            if self.save_empty and layer == 0:
                # only layer 0 is used as sentinel
                self.mark_empty(level, tx, ty, layer)
            self.delete_tile(level, tx, ty, layer)
            return 'empty'

        if not supports_RGBA(ext):
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

    def delete_tile(self, level, tx, ty, layer, ext=None):
        ext, path = self.tile_path(level, tx, ty, layer, ext)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception as e:
                pass

    def get_ext(self, layer):
        return self.ext0 if layer == 0 else self.ext

    def tile_path(self, level, tx, ty, layer, ext=None):
        if ext is None:
            ext = self.get_ext(layer)
        path = os.path.join(self.path, 'layer{}_files'.format(layer),
                            str(level), '{}_{}.{}'.format(tx, ty, ext))
        return ext, path

    def load_tile(self, level, tx, ty, layer):
        ext, path = self.tile_path(level, tx, ty, layer)
        im = None
        if os.path.isfile(path):
            im = Image.open(path)
            if not supports_RGBA(ext):
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
        for layer in range(self.render_minlayer, self.render_maxlayer):
            layer_path = os.path.join(self.path, 'layer{}_files'.format(layer))
            util.ensure_folder(layer_path)
            for level in range(self.levels):
                util.ensure_folder(os.path.join(layer_path, str(level)))
            ext = self.ext0 if layer == 0 else self.ext
            w, h = self.pyramid[-1 - self.skip_level]
            dzi = DZI_TEMPLATE.format(tile_size=self.tile_size, format=ext, width=w, height=h)
            dzi_path = os.path.join(self.path, 'layer{}.dzi'.format(layer))
            with open(dzi_path, 'w') as f:
                f.write(dzi)

    def gen_map_info(self):
        w, h = self.pyramid[-1 - self.skip_level]
        info = {
            'w': w,
            'h': h,
            'skip': self.skip_level,
        }
        if hasattr(self, 'update_map_info'):
            info = self.update_map_info(info)
        return info

    def map_info_mismatch(self, new_info):
        # Stop early when map geometry layout changes to avoid mixed outputs.
        path = os.path.join(self.path, 'map_info.json')
        if not os.path.isfile(path):
            return False
        old_info = util.load_json(path)
        check_keys = ['w', 'h', 'skip', 'x0', 'y0', 'sqr']
        mismatch = util.dict_diff(old_info, new_info, keys=check_keys, left_name='old', right_name='new')
        if mismatch:
            print('map_info mismatch detected:')
            for m in mismatch:
                print('  {}'.format(m))
            return True
        return False

    def save_map_info(self, info):
        path = os.path.join(self.path, 'map_info.json')
        util.save_json_compact(path, info)

    def delete_tile_all_layers(self, existing_tiles, level, tx, ty):
        if not existing_tiles:
            return
        for layer in range(self.minlayer, self.maxlayer):
            if not existing_tiles[layer] or level >= len(existing_tiles[layer]):
                continue
            if (tx, ty) not in existing_tiles[layer][level]:
                continue
            tags = existing_tiles[layer][level][(tx, ty)][1]
            for tag in tags:
                self.delete_tile(level, tx, ty, layer, tag)

    def clear_pending_tiles(self, existing_tiles, pending, verbose):
        if not pending:
            return
        pending = pending[0] # pending only has layer 0
        if not pending:
            return
        pending_coords = [None] * len(pending)
        pending_count = 0
        for level, coord_map in enumerate(pending):
            if not coord_map:
                continue
            pending_coords[level] = set(coord_map.keys())
            pending_count += len(coord_map)
        if pending_count == 0:
            return
        if verbose:
            print('Cleaning {} stale pending coordinates'.format(pending_count))
        for level, coords in enumerate(pending_coords):
            if not coords:
                continue
            for tx, ty in coords:
                self.delete_tile_all_layers(existing_tiles, level, tx, ty)
                self.delete_tile(level, tx, ty, 0, 'pending')

    def normalize_layered_tile_map(self, tile_map):
        if not tile_map:
            return [None for _ in range(self.maxlayer - self.minlayer)]
        max_layer = tile_map.get('max_layer')
        layers = tile_map.get('layers', [])
        total_layers = self.maxlayer - self.minlayer
        missing_layers = [None] * (total_layers - len(layers))
        if missing_layers:
            layers[max_layer:max_layer] = missing_layers
        return layers

    def get_existing_tiles(self, clear_pending, verbose):
        if verbose:
            print('Scanning existing tiles.')
        existing = source_manager.collect(self.path, ['tiles', 'pending'], source_manager.SIGNATURE_MTIME, None, verbose)
        pending = self.normalize_layered_tile_map(existing['pending'])
        existing_tiles = self.normalize_layered_tile_map(existing['tiles'])
        if clear_pending:
            self.clear_pending_tiles(existing_tiles, pending, verbose)
        return existing_tiles

    def get_completed_signatures(self, existing_tiles):
        completed_sigs = [{} for _ in range(self.levels)]
        for l in range(self.minlayer, self.maxlayer):
            layer = existing_tiles[l]
            if not layer:
                 continue
            ext = self.get_ext(l)
            for level, coord_map in enumerate(layer):
                if not coord_map:
                    continue
                for coord, (mtime, tags) in coord_map.items():
                    if ext in tags or 'empty' in tags:
                        if (coord not in completed_sigs[level] or
                            mtime < completed_sigs[level][coord]):
                            completed_sigs[level][coord] = mtime
        return completed_sigs

    def compute_incremental_tasks(self, source_units, unit_size, completed_sigs):
        # compare source snapshot with completed signatures to determine which tiles are stale and which are still valid
        # collect tasks for affected tiles that need to be re-rendered, and count their dependencies for scheduling

        # calculate affected tiles (tasks) and remove invalid completed tiles
        level = self.levels - 1
        eps = self.incremental_mtime_epsilon
        tasks_by_level = [{} for _ in range(self.levels)]
        stale_coords = set()
        for coord, (mtime, sig) in source_units.items():
            sx, sy = coord
            if self.is_source_empty(sx, sy):
                continue
            sx *= unit_size
            sy *= unit_size
            affected = self.square_rect2tiles(sx, sy, unit_size, unit_size)
            for tx, ty in affected:
                if (tx, ty) in completed_sigs[level]:
                    if completed_sigs[level][(tx, ty)] >= mtime + eps:
                        continue
                    else:
                        del completed_sigs[level][(tx, ty)]
                        stale_coords.add((level, tx, ty))
                tasks_by_level[level][(tx, ty)] = 0

        # drop sigs and convert completed to sets per level
        completed_by_level = []
        for level in range(self.levels):
            if completed_sigs[level]:
                completed_by_level.append(set(completed_sigs[level].keys()))
            else:
                completed_by_level.append(set())
        return tasks_by_level, completed_by_level, stale_coords

    def remove_stale_tiles(self, existing_tiles, stale_coords, verbose):
        total = len(stale_coords)
        progress_display = util.ProgressDisplay('Cleaning stale tiles: {progress} / {total}' if verbose else '')
        for progress, (level, tx, ty) in enumerate(stale_coords, start=1):
            progress_display.update(progress=progress, total=total)
            self.delete_tile_all_layers(existing_tiles, level, tx, ty)
        progress_display.finish(progress=total, total=total)

    def add_thumbnail_tasks(self, tasks_by_level, completed_by_level, verbose):
        # tasks_by_level only have bottom level populated, add thumbnail tasks for upper levels if needed
        for level in reversed(range(1, self.levels)):
            for x, y in completed_by_level[level]:
                # thumbnail coords in upper level
                tx = x >> 1
                ty = y >> 1
                if (tx, ty) not in completed_by_level[level - 1]:
                    tasks_by_level[level - 1].setdefault((tx, ty), 0)
            for x, y in tasks_by_level[level]:
                tx = x >> 1
                ty = y >> 1
                if (tx, ty) not in completed_by_level[level - 1]:
                    tasks_by_level[level - 1].setdefault((tx, ty), 0)
                    tasks_by_level[level - 1][(tx, ty)] += 1

    def remove_skipped_tasks(self, tasks_by_level, completed_by_level, verbose):
        if self.skip_level <= 0:
            return
        gate_level = self.levels - self.skip_level - 1
        completed = completed_by_level[gate_level]
        stack = []
        for x, y in completed:
            level = gate_level + 1
            stack.append((level, x, y))
            while stack:
                level, x, y = stack.pop()
                if level >= self.levels:
                    continue
                if (x, y) in tasks_by_level[level]:
                    del tasks_by_level[level][(x, y)]
                if level + 1 < self.levels:
                    for cx, cy in lower_level_depend(x, y):
                        stack.append((level + 1, cx, cy))

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
                        size = self.tile_size << 1
                        tile = Image.new('RGBA', (size, size))
                    tile.paste(im, (self.tile_size * i, self.tile_size * j))
                    im = None
        if tile:
            tile.thumbnail((self.tile_size, self.tile_size), Image.LANCZOS)
            im_getter.get().paste(tile, (0, 0))

    def render_below(self, im_getter, layer, layer_cache):
        ext = self.get_ext(layer)
        if supports_RGBA(ext):
            return None
        for i in range(self.render_minlayer, layer):
            im_below = layer_cache[i]
            if im_below:
                im = im_getter.get()
                im.alpha_composite(im_below)

    def render_all(self, render, n, break_key=None, verbose=False, profile=0):
        if verbose:
            print('Preparing data')
        if hasattr(render, 'init_dzi'):
            render.init_dzi(self)
        util.ensure_folder(self.path)
        map_info = self.gen_map_info()
        if self.map_info_mismatch(map_info):
            print('Render stopped. Please use new output path or remove existing output to avoid mixed outputs.')
            return False
        self.save_map_info(map_info)
        if hasattr(render, 'render'):
            if verbose:
                print('Rendering non-image elements')
                start = time.time()
            render.render(self)
            if verbose:
                time_used = time.time() - start
                print('Time used: {}'.format(str(datetime.timedelta(0, time_used))))
        no_image = hasattr(render, 'NO_IMAGE') and render.NO_IMAGE
        if no_image:
            if verbose:
                print('No image to render, done')
            return True
        self.create_empty_output()
        self.render = render
        tasks_by_level, completed_by_level = self.get_tasks(verbose)
        schd = scheduling.TopologicalDziScheduler(self, break_key, verbose)
        cache_prefix = 'pzdzi.{}.'.format(os.getpid())
        worker = scheduling.TopologicalDziWorker(self, cache_prefix)
        task = mptask.Task(worker, schd, profile)
        task.run((tasks_by_level, completed_by_level), n)
        if schd.stop:
            if verbose:
                print('Render interrupted: {}'.format(schd.stop))
            return False
        if hasattr(self, 'post_process'):
            self.post_process()
        if verbose:
            print('Done')
        return True


class PZDZI(DZI):
    def pz_init(self, path, **options):
        version_info = lotheader.get_version_info(path)
        self.pz_version = version_info['pz_version']
        self.cells = lotheader.scan_headers(path)
        self.cell_size_in_block = version_info['cell_size_in_block']
        self.block_size = version_info['block_size']
        self.cell_size = version_info['cell_size']
        self.minlayer = version_info['minlayer']
        self.maxlayer = version_info['maxlayer']
        self.hash_method = options.get('hash_method')
        self.pzmap2dzi_version = options.get('pzmap2dzi_version', 'unknown')
        self.git_branch = options.get('git_branch', '')
        self.git_commit = options.get('git_commit', '')
        self.legends = options.get('legends', {})
        layer_range = options.get('layer_range', 'all')
        if layer_range != 'all':
            self.minlayer = max(self.minlayer, layer_range[0])
            self.maxlayer = min(self.maxlayer, layer_range[1])
        if self.minlayer > 0:
            self.minlayer = 0
        if self.maxlayer < 1:
            self.maxlayer = 1
        tile_align_levels = options.get('tile_align_levels', 3)
        self.align_tiles = int(2 ** (tile_align_levels - 1))

        self.render_minlayer = max(
            options.get('render_minlayer', self.minlayer), self.minlayer)
        self.render_maxlayer = min(
            options.get('render_maxlayer', self.maxlayer), self.maxlayer)
        self.layers = self.render_maxlayer - self.render_minlayer
        if options.get('verbose'):
            print('PZ version: {} , layer range [{}, {})'.format(
                  self.pz_version, self.minlayer, self.maxlayer))
        self.rect_cover = geometry.rect_cover(self.cells)

        # incremental rendering options
        self.incremental_mtime_epsilon = float(options.get('incremental_render_mtime_epsilon_sec', 1.0))
        self.delete_stale_tiles = options.get('delete_stale_tiles', False)
        # per render options
        self.source_path = options.get('source_path', 'input')

        source_unit_size = options.get('source_unit_size', 'cell')
        if source_unit_size == 'cell':
            self.source_unit_size = self.cell_size
        elif source_unit_size == 'block':
            self.source_unit_size = self.block_size
        else:
            self.source_unit_size = int(source_unit_size)
        source_tags = options.get('source_tags', ['map_source'])
        source_tags = source_tags if source_tags else []
        if not isinstance(source_tags, list):
            source_tags = [source_tags]
        self.source_tags = source_tags
        cell_range = options.get('cell_range', 'all')
        self.init_unit_range(cell_range)

    def init_unit_range(self, cell_range):
        self.unit_range = []
        if cell_range != 'all':
            for rect in cell_range:
                if len(rect) == 2:
                    rect.extend([1, 1])
                x, y, w, h = rect
                sx = x * self.cell_size
                sy = y * self.cell_size
                ex = sx + w * self.cell_size
                ey = sy + h * self.cell_size
                ux = sx // self.source_unit_size
                uy = sy // self.source_unit_size
                uw = (ex - 1) // self.source_unit_size - ux + 1
                uh = (ey - 1) // self.source_unit_size - uy + 1
                self.unit_range.append((ux, uy, uw, uh))
        print('Unit range: {}'.format(self.unit_range if self.unit_range else 'all'))

    def filter_source_by_unit_range(self, coord_map):
        if not self.unit_range:
            return {}
        to_delete = []
        for coord in coord_map:
            ux, uy = coord
            cx = ux * self.source_unit_size // self.cell_size
            cy = uy * self.source_unit_size // self.cell_size
            for rx, ry, rw, rh in self.unit_range:
                if rx <= cx < rx + rw and ry <= cy < ry + rh:
                    break
            else:
                to_delete.append(coord)
        deleted = {}
        for coord in to_delete:
            deleted[coord] = coord_map[coord]
            del coord_map[coord]
        return deleted

    def update_pz_map_info(self, info):
        info['cell_size'] = self.cell_size
        info['block_size'] = self.block_size
        info['pz_version'] = self.pz_version
        info['maxlayer'] = self.maxlayer
        info['minlayer'] = self.minlayer
        info['pzmap2dzi_version'] = self.pzmap2dzi_version
        info['git_branch'] = self.git_branch
        info['git_commit'] = self.git_commit
        info['legends'] = self.legends
        info['cell_rects'] = self.rect_cover
        return info

    def is_source_empty(self, cx, cy):
        # check if in range
        if self.unit_range:
            for ux, uy, uw, uh in self.unit_range:
                if ux <= cx < ux + uw and uy <= cy < uy + uh:
                    break
            else:
                return True
        # legacy render.valid_cell() check
        if self.source_unit_size != self.cell_size:
            return False
        if not hasattr(self.render, 'valid_cell'):
            return False
        return not self.render.valid_cell(cx, cy)

    def get_source_snapshot(self, last_units, verbose):
        source_path = getattr(self.render, self.source_path, None)
        if not source_path:
            return {}
        if not self.source_tags:
            return {}
        if verbose:
            print('Scanning source files.')
        mode = source_manager.SIGNATURE_MTIME
        if self.hash_method:
            mode |= source_manager.SIGNATURE_HASH
        sources = source_manager.collect(source_path, self.source_tags, mode, self.hash_method, verbose)
        snapshot = {}
        if len(self.source_tags) == 1:
            snapshot = sources.get(self.source_tags[0])
        else:
            for tag in self.source_tags:
                for coord, sig in sources.get(tag, {}).items():
                    cur = snapshot.get(coord)
                    if cur is None:
                        snapshot[coord] = sig
                        continue
                    # Keep the newest signature when multiple tags contribute.
                    cur_mtime, cur_sig_hash = cur
                    mtime, sig_hash = sig
                    latest_mtime = max(cur_mtime, mtime)
                    snapshot[coord] = latest_mtime, source_manager.merge_sigs(cur_sig_hash, sig_hash)
        self.filter_source_by_unit_range(snapshot)
        snapshot_copy = snapshot.copy()
        if last_units:
            deleted = self.filter_source_by_unit_range(last_units.map)
            snapshot_copy.update(deleted)
        coord_map = util.CoordMap(snapshot_copy, {'hash_method': self.hash_method})
        util.save_coord_map(self.source_snapshot_path_wip, coord_map)
        if last_units:
            self.filter_source_by_unit_range(last_units.map)
            now = time.time() + 1
            compare_hash = bool(self.hash_method) and last_units.metadata.get('hash_method') == self.hash_method
            for coord, sig in last_units.map.items():
                if not isinstance(coord, tuple):
                    continue
                # deleted source
                if coord not in snapshot:
                    snapshot[coord] = (now, 'deleted')
                    continue
                last_mtime, last_sig_hash = sig
                new_mtime, new_sig_hash = snapshot[coord]
                if compare_hash:
                    # hash changed
                    if last_sig_hash != new_sig_hash:
                        snapshot[coord] = (now, new_sig_hash)
                else:
                    # mtime changed
                    if last_mtime != new_mtime:
                        snapshot[coord] = (now, new_sig_hash)
        return snapshot

    def get_tasks(self, verbose):
        # return tasks_by_level: List[Dict[Tuple[int, int], int]], completed_by_level: List[Set[Tuple[int, int]]]
        # tasks_by_level[layer][(tx, ty)] = dependency count for the task
        #     indicate number of lower level tiles that need to be completed before this tile can be rendered
        #     not including already completed lower level tiles
        # completed_by_level[layer] = set of (tx, ty) that are already completed

        self.source_snapshot_path = os.path.join(self.path, 'sources.json')
        self.source_snapshot_path_wip = os.path.join(self.path, 'sources_current.json')

        last_units = util.load_coord_map(self.source_snapshot_path)
        source_units = self.get_source_snapshot(last_units, verbose)

        # get existing tiles and clean up pending tiles
        existing_tiles = self.get_existing_tiles(clear_pending=True, verbose=verbose)

        completed_sigs = self.get_completed_signatures(existing_tiles)
        tasks = self.compute_incremental_tasks(source_units, self.source_unit_size, completed_sigs)
        tasks_by_level, completed_by_level, stale_coords = tasks
        print('Stale tiles: {}, Affected tiles: {}'.format(len(stale_coords), sum(len(t) for t in tasks_by_level)))

        if self.delete_stale_tiles and stale_coords:
            self.remove_stale_tiles(existing_tiles, stale_coords, verbose)
        self.add_thumbnail_tasks(tasks_by_level, completed_by_level, verbose)
        self.remove_skipped_tasks(tasks_by_level, completed_by_level, verbose)
        return tasks_by_level, completed_by_level

    def post_process(self):
        # post process after all tiles are rendered
        self.finalize_snapshot()

    def finalize_snapshot(self):
        if os.path.isfile(self.source_snapshot_path_wip):
            if os.path.isfile(self.source_snapshot_path):
                try:
                    os.remove(self.source_snapshot_path)
                except Exception:
                    print('WARNING: failed to remove old source snapshot')
            try:
                os.rename(self.source_snapshot_path_wip, self.source_snapshot_path)
            except Exception:
                print('WARNING: failed to finalize source snapshot')


class IsoDZI(PZDZI):
    SQUARE_HEIGHT = 64
    GRID_HEIGHT = SQUARE_HEIGHT // 2  # 32
    SQUARE_WIDTH = 128
    GRID_WIDTH = SQUARE_WIDTH // 2  # 64
    LAYER_HEIGHT = 192
    GRID_HEIGHT_PER_LAYER = LAYER_HEIGHT // GRID_HEIGHT  # 6
    # normal texture size      w:128 h:256
    TEXTURE_WIDTH = 128
    TEXTURE_HEIGHT = 256
    # jumbo tree texutre size  w:384 h:512
    LARGE_TEXTURE_WIDTH = 384
    LARGE_TEXTURE_HEIGHT = 512

    def get_sqr_center(self, gx, gy):
        ox = gx * IsoDZI.GRID_WIDTH
        oy = gy * IsoDZI.GRID_HEIGHT
        return ox, oy

    def __init__(self, map_path, **options):
        self.pz_init(map_path, **options)
        self.sqr_height = IsoDZI.SQUARE_HEIGHT
        self.sqr_width = IsoDZI.SQUARE_WIDTH
        self.tile_size = options.get('tile_size', 1024)
        self.grid_per_tilex = self.tile_size // IsoDZI.GRID_WIDTH
        self.grid_per_tiley = self.tile_size // IsoDZI.GRID_HEIGHT
        # always assume large texture for output size calculation
        # to ensure alignment between base map and overlays
        self.output_margin = self.get_output_margin()
        self.render_margin = options.get('render_margin')
        if isinstance(self.render_margin, str):
            texture_size = self.render_margin.lower()
            self.render_margin = self.get_texture_render_margin(texture_size == 'large')
        # if render margin is a falsy value, (0, 0, 0, 0) will be used
        self.affected_margin = self.render2affected(self.render_margin, 'render')
        self.affected_margin_single_layers = self.render2affected(self.render_margin, 'single')
        if options.get('debug'):
            print('output margin', self.output_margin)
            print('render margin', self.render_margin)
            print('affected margin', self.affected_margin)
            print('affected margin single layers', self.affected_margin_single_layers)

        assert self.tile_size % self.sqr_width == 0
        assert self.tile_size % self.sqr_height == 0
        assert len(self.cells) > 0
        gxmin, gymin, gxmax, gymax = [None] * 4
        for cx, cy in self.cells:
            left, top, right, bottom = self.cell_grid_bound(cx, cy)
            if gxmin is None:
                gxmin = left
                gymin = top
                gxmax = right
                gymax = bottom
            else:
                gxmin = min(left, gxmin)
                gymin = min(top, gymin)
                gxmax = max(right, gxmax)
                gymax = max(bottom, gymax)

        gbox = gxmin, gymin, gxmax, gymax
        gxmin, gymin, gxmax, gymax = map(sum, zip(gbox, self.output_margin))

        # grid offset
        self.gxo = align_origin(gxmin, self.grid_per_tilex * self.align_tiles)
        self.gyo = align_origin(gymin, self.grid_per_tiley * self.align_tiles)
        self.gw = gxmax - self.gxo
        self.gh = gymax - self.gyo
        w = self.gw * IsoDZI.GRID_WIDTH
        h = self.gh * IsoDZI.GRID_HEIGHT
        DZI.__init__(self, w, h, **options)

    def get_output_margin(self):
        # largest affected area of a square from its center in grid coordinates
        render_margin = self.get_texture_render_margin(True)
        return self.render2affected(render_margin, 'output')

    def render2affected(self, margin, layer_range='render'):
        # convert render margin for one tile to affecting margin for a square from its center
        minlayer, maxlayer = self.minlayer, self.maxlayer
        if layer_range in ['all', 'output']:
            minlayer, maxlayer = self.minlayer, self.maxlayer
        elif layer_range == 'render':
            minlayer, maxlayer = self.render_minlayer, self.render_maxlayer
        elif layer_range == 'single':
            minlayer, maxlayer = 0, 1
        left, top, right, bottom = margin if margin else (0, 0, 0, 0)
        # the square size itself is 2x2 in grid coordinates, so add 1 to each side
        left, top, right, bottom = -1 - right, -1 - bottom, 1 - left, 1 - top
        if minlayer < 0:
            bottom -= minlayer * IsoDZI.GRID_HEIGHT_PER_LAYER
        if maxlayer > 1:
            top -= maxlayer * IsoDZI.GRID_HEIGHT_PER_LAYER
        return left, top, right, bottom

    def get_texture_render_margin(self, use_large_texture=None):
        # source outside of a tile that may affect the tile in grid coordinates on the same layer
        texture_width = IsoDZI.TEXTURE_WIDTH
        texture_height = IsoDZI.TEXTURE_HEIGHT
        if use_large_texture:
            texture_width = IsoDZI.LARGE_TEXTURE_WIDTH
            texture_height = IsoDZI.LARGE_TEXTURE_HEIGHT
        width = (texture_width // 2) // IsoDZI.GRID_WIDTH - 1
        left = -width
        right = width
        top = 0
        bottom = (texture_height // IsoDZI.GRID_HEIGHT) - 2
        return left, top, right, bottom

    def tile2grid(self, tx, ty, layer):
        gx = self.gxo + self.grid_per_tilex * tx
        gy = self.gyo + self.grid_per_tiley * ty
        gy += IsoDZI.GRID_HEIGHT_PER_LAYER * layer
        return gx, gy

    def square_grid_bound(self, sx1, sy1, sx2, sy2):
        left = sx1 - sy2
        top = sx1 + sy1
        right = sx2 - sy1
        bottom = sx2 + sy2
        return left, top, right, bottom

    def cell_grid_bound(self, cx, cy):
        sxmin = cx * self.cell_size
        symin = cy * self.cell_size
        sxmax = sxmin + self.cell_size - 1
        symax = symin + self.cell_size - 1
        return self.square_grid_bound(sxmin, symin, sxmax, symax)

    def square_rect2tiles_rough(self, sx, sy, w, h):
        sx2 = sx + w - 1
        sy2 = sy + h - 1
        gbox = map(sum, zip(self.square_grid_bound(sx, sy, sx2, sy2), self.affected_margin))
        left, top, right, bottom = gbox
        txmin = (left - self.gxo) // self.grid_per_tilex
        txmax = (right - self.gxo) // self.grid_per_tilex
        tymin = (top - self.gyo) // self.grid_per_tiley
        tymax = (bottom - self.gyo) // self.grid_per_tiley
        tiles = [(tx, ty) for ty in range(tymin, tymax + 1)
                 for tx in range(txmin, txmax + 1)]
        return tiles

    def square_rect2oct(self, sx, sy, w, h, margin=None):
        # calculate the affected octagon of a square rect in grid coordinates with output margin
        #
        # Vertices are computed in (gx, gy) order clockwise:
        #   T(top), R(right), B(bottom), L(left)
        #
        # diamond (from square rect)               octagon (after margins)
        #                                             (0) ___ (1)
        #            T  (gx, gy)                         /   \
        #           / \                            (7)  /     \  (2)
        #          /   \                               |       |
        #         L     R          expand by           |       |
        #          \   /        ---------------->      |       |
        #           \ /                            (6)  \     /  (3)
        #            B  (gx2, gy2)                       \___/
        #                                             (5)     (4)

        # calculate square coordinates for bottom
        sx2 = sx + w - 1
        sy2 = sy + h - 1

        # Rectangle in (sx, sy) maps to a diamond in (gx, gy).
        top = (sx - sy, sx + sy)
        right = (sx2 - sy, sx2 + sy)
        bottom = (sx2 - sy2, sx2 + sy2)
        left = (sx - sy2, sx + sy2)

        # Expand upper hull upward, lower hull downward, then widen sides.
        if margin is None:
            margin = self.affected_margin
        margin_left, margin_top, margin_right, margin_bottom = margin

        octagon = [
            (top[0] + margin_left, top[1] + margin_top),
            (top[0] + margin_right, top[1] + margin_top),
            (right[0] + margin_right, right[1] + margin_top),
            (right[0] + margin_right, right[1] + margin_bottom),
            (bottom[0] + margin_right, bottom[1] + margin_bottom),
            (bottom[0] + margin_left, bottom[1] + margin_bottom),
            (left[0] + margin_left, left[1] + margin_bottom),
            (left[0] + margin_left, left[1] + margin_top),
        ]
        return octagon

    def square_rect2tiles(self, sx, sy, w, h, margin=None):
        octagon = self.square_rect2oct(sx, sy, w, h, margin)
        n = len(octagon)

        gy_min = min(v[1] for v in octagon)
        gy_max = max(v[1] for v in octagon)
        tymin = (gy_min - self.gyo) // self.grid_per_tiley
        tymax = (gy_max - self.gyo - 1) // self.grid_per_tiley

        tiles = []
        for ty in range(tymin, tymax + 1):
            tile_gy0 = self.gyo + ty * self.grid_per_tiley
            tile_gy1 = tile_gy0 + self.grid_per_tiley

            gx_lo = None
            gx_hi = None

            for i in range(n):
                x0, y0 = octagon[i - 1]
                x1, y1 = octagon[i]
                if y0 > y1:
                    x0, y0, x1, y1 = x1, y1, x0, y0

                if y1 < tile_gy0 or y0 > tile_gy1:
                    continue

                if y0 == y1:
                    lo = min(x0, x1)
                    hi = max(x0, x1)
                else:
                    cl_y0 = max(y0, tile_gy0)
                    cl_y1 = min(y1, tile_gy1)
                    dy = y1 - y0
                    dx = x1 - x0
                    num0 = (cl_y0 - y0) * dx
                    num1 = (cl_y1 - y0) * dx
                    lo = x0 + (min(num0, num1) // dy)
                    hi = x0 + (-(-max(num0, num1) // dy)) # ceil

                if gx_lo is None or lo < gx_lo:
                    gx_lo = lo
                if gx_hi is None or hi > gx_hi:
                    gx_hi = hi

            if gx_lo is None:
                continue

            txmin = (gx_lo - self.gxo) // self.grid_per_tilex
            txmax = (gx_hi - self.gxo - 1) // self.grid_per_tilex
            for tx in range(txmin, txmax + 1):
                tiles.append((tx, ty))

        return tiles

    def render_tile(self, im_getter, tx, ty, layer, layer_cache):
        self.render_below(im_getter, layer, layer_cache)
        gx0, gy0 = self.tile2grid(tx, ty, layer)

        if hasattr(self.render, 'tile'):
            return self.render.tile(im_getter, self, gx0, gy0, layer)

        gx1 = gx0 + self.grid_per_tilex
        gy1 = gy0 + self.grid_per_tiley
        gbox = gx0, gy0, gx1, gy1
        if self.render_margin:
            gbox = map(sum, zip(gbox, self.render_margin))
        left, top, right, bottom = gbox
        for gy in range(top, bottom + 1):
            for gx in range(left, right + 1):
                if (gx + gy) & 1:
                    continue
                sx = (gx + gy) >> 1
                sy = (gy - gx) >> 1
                ox, oy = self.get_sqr_center(gx - gx0, gy - gy0)
                self.render.square(im_getter, self, ox, oy, sx, sy, layer)

    def update_map_info(self, info):
        info = self.update_pz_map_info(info)
        info['x0'] = -self.gxo * IsoDZI.GRID_WIDTH
        info['y0'] = -(self.gyo + 1) * IsoDZI.GRID_HEIGHT  # center to top
        info['sqr'] = 2 * IsoDZI.GRID_WIDTH
        return info


class TopDZI(PZDZI):
    def __init__(self, map_path, **options):
        self.pz_init(map_path, **options)
        self.square_size = options.get('top_view_square_size', 1)

        cxmax, cymax = map(max, zip(*self.cells))
        cxmin, cymin = map(min, zip(*self.cells))

        self.cxo = align_origin(cxmin, self.align_tiles)
        self.cyo = align_origin(cymin, self.align_tiles)
        self.cw = cxmax - self.cxo + 1
        self.ch = cymax - self.cyo + 1
        self.tile_size = self.square_size * self.cell_size
        w = self.tile_size * self.cw
        h = self.tile_size * self.ch
        DZI.__init__(self, w, h, **options)

    def tile2cell(self, tx, ty):
        cx = tx + self.cxo
        cy = ty + self.cyo
        return cx, cy

    def square_rect2tiles(self, sx, sy, w, h, margin=None):
        sx2 = sx + w - 1
        sy2 = sy + h - 1

        cxmin = sx // self.cell_size
        cymin = sy // self.cell_size
        cxmax = sx2 // self.cell_size
        cymax = sy2 // self.cell_size

        tiles = []
        for cy in range(cymin, cymax + 1):
            for cx in range(cxmin, cxmax + 1):
                tiles.append((cx - self.cxo, cy - self.cyo))
        return tiles

    def render_tile(self, im_getter, tx, ty, layer, layer_cache):
        self.render_below(im_getter, layer, layer_cache)
        cx, cy = self.tile2cell(tx, ty)
        if hasattr(self.render, 'tile'):
            return self.render.tile(im_getter, self, cx, cy, layer)

        sx = cx * self.cell_size
        sy = cy * self.cell_size
        for x in range(self.cell_size):
            for y in range(self.cell_size):
                ox = x * self.square_size
                oy = y * self.square_size
                self.render.square(im_getter, self, ox, oy, sx + x, sy + y, layer)

    def update_map_info(self, info):
        info = self.update_pz_map_info(info)
        info['x0'] = -(self.cxo * self.square_size * self.cell_size)
        info['y0'] = -(self.cyo * self.square_size * self.cell_size)
        info['sqr'] = self.square_size
        return info
