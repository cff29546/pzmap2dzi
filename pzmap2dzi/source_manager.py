import os
import re
import hashlib

from . import util

SIGNATURE_NONE = 0
SIGNATURE_MTIME = 1
SIGNATURE_HASH = 2
SIGNATURE_PATH = 4
SIGNATURE_MAX = SIGNATURE_MTIME | SIGNATURE_HASH | SIGNATURE_PATH


class PathPattern:
    __slots__ = ('output_name', 'pattern', 'output_type', 'parser')

    def __init__(self, output_name, pattern, output_type, parser):
        self.output_name = output_name
        self.pattern = pattern
        self.output_type = output_type
        self.parser = parser


class SignatureAggregate:
    def __init__(self):
        self.mtime = 0
        self.sigs = []

    def add(self, mtime, sig):
        if mtime and mtime > self.mtime:
            self.mtime = mtime
        if sig:
            self.sigs.append(sig)

    def value(self):
        return self.mtime, sorted(self.sigs)

    def tags(self):
        return self.mtime, set(self.sigs)

def _normalize_rel_path(path):
    return path.replace('\\', '/')


def _file_digest(path, hash_algo, chunk_size=1024 * 1024):
    hasher = hashlib.new(hash_algo)
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


class SignatureCollector:
    def __init__(self, patterns, mode=SIGNATURE_MTIME, hash_algo='sha256', progress=True):
        if mode < 0 or mode > SIGNATURE_MAX:
            raise ValueError('Unknown signature mode: {}'.format(mode))
        self.patterns = patterns
        self.mode = mode
        self.hash_algo = hash_algo
        self.progress = progress

    def _collect_raw_paths(self, root_path):
        if not os.path.isdir(root_path):
            raise ValueError('Not a folder path: {}'.format(root_path))
        folders = []
        file_count = 0
        for root, _, file_names in os.walk(root_path):
            folders.append((root, file_names))
            file_count += len(file_names)
        if self.progress:
            print('{} files detected.'.format(file_count))
        return folders, file_count

    def collect(self, root_path):
        folders, total = self._collect_raw_paths(root_path)
        output_defs = {}
        for pattern in self.patterns:
            if pattern.output_name in output_defs:
                continue
            output_defs[pattern.output_name] = {
                'type': pattern.output_type,
                'simple': {},
                'tile': {},
                'min_layer': None,
                'max_layer': None,
                'max_level': -1,
            }

        progress_display = util.ProgressDisplay('Scanning files: {percent: >3}%') if self.progress else None
        progress_state = -1
        index = 0
        for root, file_names in folders:
            rel_root = _normalize_rel_path(os.path.relpath(root, root_path)) + '/'
            if rel_root == './':
                rel_root = ''
            for file_name in file_names:
                index += 1
                if progress_display and total > 0:
                    percent = (index * 100) // total
                    if percent > progress_state:
                        progress_display.update(percent=percent)
                        progress_state = percent
                mtime = None
                digest = None
                abs_path = None
                rel_path = rel_root + file_name

                for pattern in self.patterns:
                    match = pattern.pattern.match(rel_path)
                    if not match:
                        continue

                    if abs_path is None and self.mode != SIGNATURE_NONE:
                        abs_path = os.path.join(root, file_name)
                    sig = None
                    if (self.mode & SIGNATURE_MTIME) and mtime is None:
                        mtime = os.path.getmtime(abs_path)
                    if (self.mode & SIGNATURE_HASH) and digest is None:
                        digest = _file_digest(abs_path, self.hash_algo)
                        sig = '{}:{}'.format(rel_path, digest)
                    if (self.mode & SIGNATURE_PATH):
                        sig = abs_path

                    parsed = pattern.parser(match)
                    out = output_defs[pattern.output_name]
                    if pattern.output_type == 'simple':
                        key = parsed['coord']
                        agg = out['simple'].get(key)
                        if agg is None:
                            agg = SignatureAggregate()
                            out['simple'][key] = agg
                        agg.add(mtime, sig)
                    elif pattern.output_type == 'tile':
                        layer = parsed['layer']
                        level = parsed['level']
                        key = parsed['coord']
                        ext = parsed['ext']
                        tile_key = (layer, level, key)
                        agg = out['tile'].get(tile_key)
                        if agg is None:
                            agg = SignatureAggregate()
                            out['tile'][tile_key] = agg
                        agg.add(mtime, ext)

                        if out['min_layer'] is None or layer < out['min_layer']:
                            out['min_layer'] = layer
                        if out['max_layer'] is None or layer > out['max_layer']:
                            out['max_layer'] = layer
                        if level > out['max_level']:
                            out['max_level'] = level
                    else:
                        raise ValueError('Unknown output type: {}'.format(pattern.output_type))

        if progress_display:
            progress_display.finish(percent=100)

        result = {}
        for name, out in output_defs.items():
            if out['type'] == 'simple':
                result[name] = {coord: agg.value() for coord, agg in out['simple'].items()}
                continue

            min_layer = out['min_layer']
            max_layer = out['max_layer']
            max_level = out['max_level']
            if min_layer is None or max_layer is None or max_level < 0:
                result[name] = {
                    'min_layer': None,
                    'max_layer': None,
                    'max_level': -1,
                    'layers': [],
                }
                continue

            neg_count = -min_layer if min_layer < 0 else 0
            max_layer += 1
            total_layers = max_layer + neg_count
            layers = [[{} for _ in range(max_level + 1)] for _ in range(total_layers)]

            for (layer, level, coord), agg in out['tile'].items():
                layers[layer][level][coord] = agg.tags()
            result[name] = {
                'min_layer': min_layer,
                'max_layer': max_layer,
                'max_level': max_level,
                'layers': layers,
            }
        return result


def _2d_coord_map(match):
    return {'coord': (int(match.group(1)), int(match.group(2)))}


def _tile_map(match):
    return {
        'layer': int(match.group(1)),
        'level': int(match.group(2)),
        'coord': (int(match.group(3)), int(match.group(4))),
        'ext': match.group(5),
    }


def default_patterns():
    return [
        PathPattern('map_source', re.compile(r'^(\d+)_(\d+)\.lotheader$'), 'simple', _2d_coord_map),
        PathPattern('map_source', re.compile(r'^world_(\d+)_(\d+)\.lotpack$'), 'simple', _2d_coord_map),
        PathPattern('foraging', re.compile(r'^maps/biomemap_(\d+)_(\d+)\.png$'), 'simple', _2d_coord_map),
        PathPattern('save', re.compile(r'^map_(\d+)_(\d+)\.bin$'), 'simple', _2d_coord_map),
        PathPattern('save', re.compile(r'^map/map_(\d+)_(\d+)\.bin$'), 'simple', _2d_coord_map),
        PathPattern('save', re.compile(r'^map/(\d+)/(\d+)\.bin$'), 'simple', _2d_coord_map),
        PathPattern('tiles', re.compile(r'^layer(-?\d+)_files/(\d+)/(\d+)_(\d+)\.(png|webp|jpg|empty)$'), 'tile', _tile_map),
        PathPattern('pending', re.compile(r'^layer(-?\d+)_files/(\d+)/(\d+)_(\d+)\.(pending)$'), 'tile', _tile_map),
    ]


def patterns_by_names(names):
    wanted = set(names)
    return [p for p in default_patterns() if p.output_name in wanted]


def collect(root_path, tag_names, signature_mode, hash_algo='sha256', progress=True):
    collector = SignatureCollector(
        patterns_by_names(tag_names),
        mode=signature_mode,
        hash_algo=hash_algo,
        progress=progress,
    )
    result = collector.collect(root_path)
    for tag in tag_names:
        result.setdefault(tag, None)
    return result


def merge_sigs(sigs1, sigs2):
    if not sigs1:
        return sigs2
    if not sigs2:
        return sigs1
    # combine two ordered list of strings and ensure order
    # use merge sort
    merged = []
    i, j = 0, 0
    while i < len(sigs1) and j < len(sigs2):
        if sigs1[i] < sigs2[j]:
            merged.append(sigs1[i])
            i += 1
        else:
            merged.append(sigs2[j])
            j += 1
    merged.extend(sigs1[i:])
    merged.extend(sigs2[j:])
    return merged

