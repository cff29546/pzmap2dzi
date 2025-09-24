import sys
import os
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_BASE_DIR, '..'))
_DEFAULT_CONF = os.path.join(_BASE_DIR, '../conf/conf.yaml')
try:
    import main
    from pzmap2dzi import lotheader, texture
except ImportError:
    raise


def get_used_tiles(path):
    headers = lotheader.load_all_headers(path)
    used = set()
    for header in headers.values():
        used.update(header['tiles'])
    return sorted(list(used))


def get_pack_textures(path):
    tl = texture.TextureLibrary()
    tl.add_pack(path)
    return tl.lib.keys()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='tiles checker')
    parser.add_argument('-c', '--conf', type=str, default=_DEFAULT_CONF)
    args = parser.parse_args()

    map_path = main.get_map_path(args.conf, 'default')
    used = get_used_tiles(map_path)

    texture_path = os.path.join(map_path, '..', '..', 'texturepacks')
    packs = {}
    for name in os.listdir(texture_path):
        if name.endswith('.pack') and '1x' not in name and 'temp' not in name:
            pack = os.path.join(texture_path, name)
            packs[name] = get_pack_textures(pack)

    print('\nUsed: {}'.format(len(used)))
    count = {}
    for tile in used:
        count[tile] = []

    for name, tiles in packs.items():
        hit = 0
        for tile in tiles:
            if tile in used:
                count[tile].append(name)
                hit += 1
        print('{}: {}/{}'.format(name, hit, len(tiles)))

    missing = []
    multi = []
    for tile, names in count.items():
        if len(names) == 0:
            missing.append(tile)
        if len(names) > 1:
            multi.append([tile, names])

    print('Multi-mapped tiles: {}'.format(len(multi)))
    print('Missing tiles: {}'.format(len(missing)))

    for tile in sorted(missing):
        print('  {}'.format(tile))
