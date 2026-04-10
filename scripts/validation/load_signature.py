import sys
import os
import time
import argparse
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CONF = os.path.join(_BASE_DIR, '../../conf/conf.yaml')

sys.path.append(os.path.join(_BASE_DIR, '..', '..'))
from pzmap2dzi import source_manager


def _collect(root_path, output_name, signature_mode, hash_algo='sha1'):
    if signature_mode == 'time':
        signature_mode = source_manager.SIGNATURE_MTIME
    elif signature_mode == 'hash':
        signature_mode = source_manager.SIGNATURE_HASH
    elif signature_mode == 'both':
        signature_mode = source_manager.SIGNATURE_MTIME | source_manager.SIGNATURE_HASH
    else:
        signature_mode = 0
    collector = source_manager.SignatureCollector(
        source_manager.patterns_by_names([output_name]),
        mode=signature_mode,
        hash_algo=hash_algo,
        progress=True,
    )
    return collector.collect(root_path).get(output_name)


def cells(conf_path=None, map_path=None, signature_mode='time', hash_algo='sha1'):
    if map_path is None:
        import main
        map_path = main.get_map_path(conf_path or _DEFAULT_CONF, 'default')
    data = _collect(map_path, 'map_source', signature_mode, hash_algo=hash_algo)
    print('Cells: {}'.format(len(data)))


def save(save_path, signature_mode='time', hash_algo='sha1'):
    data = _collect(save_path, 'save', signature_mode, hash_algo=hash_algo)
    print('Save: {}, Blocks: {}'.format(save_path, len(data)))


def saves(signature_mode='time', hash_algo='sha1'):
    save_root = os.path.expandvars('%UserProfile%\\zomboid\\Saves')
    for mode in os.listdir(save_root):
        mode_path = os.path.join(save_root, mode)
        if os.path.isdir(mode_path):
            for name in os.listdir(mode_path):
                save_path = os.path.join(mode_path, name)
                if os.path.isdir(save_path):
                    save(save_path, signature_mode=signature_mode, hash_algo=hash_algo)


def foraging(conf_path=None, map_path=None, signature_mode='time', hash_algo='sha1'):
    if map_path is None:
        import main
        map_path = main.get_map_path(conf_path or _DEFAULT_CONF, 'default')
    data = _collect(map_path, 'foraging', signature_mode, hash_algo=hash_algo)
    print('Foraging Cells: {}'.format(len(data)))


def tile_stats(tile_output, signature_mode):
    min_layer = tile_output.get('min_layer')
    max_layer = tile_output.get('max_layer')
    max_level = tile_output.get('max_level')
    layers = tile_output.get('layers', [])

    print('Layers list length: {}'.format(len(layers)))
    print('Layer range: {} to {}'.format(min_layer, max_layer))
    print('Max level: {}'.format(max_level))

    if len(layers) != (max_layer - min_layer):
        print('Warning: Layer list length does not match layer range.')
        return

    for layer_idx in range(min_layer, max_layer + 1):
        levels = layers[layer_idx]
        if not levels:
            continue
        tile_count = sum(len(tiles) for tiles in levels)
        if tile_count == 0:
            continue
        mtimes = []
        for tiles in levels:
            mtimes.extend(mtime for mtime, _ in tiles.values())
        earliest = time.ctime(min(mtimes)) if mtimes else 'n/a'
        latest = time.ctime(max(mtimes)) if mtimes else 'n/a'
        print('Layer index {}, Levels: {}, Tiles: {}, Earliest: {}, Latest: {}'.format(
            layer_idx, len(levels), tile_count, earliest, latest))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='mtime collector')
    parser.add_argument('path', help='command to execute or folder path to collect mtime')
    parser.add_argument('--conf', help='config file path', default=_DEFAULT_CONF)
    parser.add_argument(
        '-s',
        '--signature',
        choices=['time', 'hash', 'both'],
        default='time',
        help='signature output mode',
    )
    parser.add_argument('-a', '--hash-algo', default='sha1', help='hashlib algorithm name for hash/both signature modes')
    args = parser.parse_args()

    start = time.time()
    if os.path.isdir(args.path):
        tile_output = _collect(args.path, 'tiles', args.signature, hash_algo=args.hash_algo)
        tile_stats(tile_output, args.signature)
    elif args.path == 'cells':
        cells(conf_path=args.conf, signature_mode=args.signature, hash_algo=args.hash_algo)
    elif args.path == 'foraging':
        foraging(conf_path=args.conf, signature_mode=args.signature, hash_algo=args.hash_algo)
    elif args.path == 'saves':
        saves(signature_mode=args.signature, hash_algo=args.hash_algo)
    else:
        print('Unknown command or non-existing folder path: {}'.format(args.path))
    print('Total elapsed: {:.2f}s'.format(time.time() - start))