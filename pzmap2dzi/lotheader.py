import os
import re
from . import binfile, util

VERSION_LIMITATIONS = {
    0: {  # B41
        'CELL_SIZE_IN_BLOCKS': 30,
        'BLOCK_SIZE_IN_SQUARES': 10,
        'MIN_LAYER':  0,
        'MAX_LAYER':  8,
    },
    1: {  # B42
        'CELL_SIZE_IN_BLOCKS': 32,
        'BLOCK_SIZE_IN_SQUARES':  8,
        'MIN_LAYER': -32,
        'MAX_LAYER': 32,
    },
}

HEADER_FILE_PATTERN = re.compile('(\\d+)_(\\d+)\\.lotheader$')


def load_all_headers(path, first_only=False):
    headers = {}
    for f in os.listdir(path):
        m = HEADER_FILE_PATTERN.match(f)
        if not m:
            continue

        x, y = map(int, m.groups())
        headers[x, y] = load_lotheader(path, x, y)
        if first_only:
            return headers
    return headers


def get_version_info(path, fast_mode=False):
    headers = load_all_headers(path, fast_mode)
    cells = set()
    version = set()
    minlayer = []
    maxlayer = []
    cell_size_in_block = set()
    block_size = set()
    for (x, y), header in headers.items():
        cells.add((x, y))
        version.add(header['version'])
        minlayer.append(header['minlayer'])
        maxlayer.append(header['maxlayer'])
        cell_size_in_block.add(header['CELL_SIZE_IN_BLOCKS'])
        block_size.add(header['BLOCK_SIZE_IN_SQUARES'])
    if len(version) != 1:
        raise Exception('Inconsistent version: {}'.format(version))
    if len(cell_size_in_block) != 1:
        bpc = list(cell_size_in_block)
        raise Exception('Inconsistent block_per_cell: {}'.format(bpc))
    if len(block_size) != 1:
        raise Exception('Inconsistent block_size: {}'.format(block_size))
    version = version.pop()
    cell_size_in_block = cell_size_in_block.pop()
    block_size = block_size.pop()
    cell_size = cell_size_in_block*block_size
    minlayer = min(minlayer)
    maxlayer = max(maxlayer)
    version_info = {
        'version': version,
        'cells': cells,
        'cell_size_in_block': cell_size_in_block,
        'block_size': block_size,
        'cell_size': cell_size,
        'minlayer': minlayer,
        'maxlayer': maxlayer,
    }
    return version_info


def read_zpop(data, pos, size):
    zpop = []
    for x in range(size):
        line = []
        for y in range(size):
            pop, pos = util.read_uint8(data, pos)
            line.append(pop)
        zpop.append(line)
    return zpop, pos


def load_lotheader(path, x, y):
    data = b''
    header = {}
    lotheader = os.path.join(path, '{}_{}.lotheader'.format(x, y))
    if not os.path.isfile(lotheader):
        return None

    with open(lotheader, 'rb') as f:
        data = f.read()

    header['path'] = path
    header['x'] = x
    header['y'] = y

    version, pos = binfile.get_version(data, 0, b'LOTH', util.read_uint32)
    header.update(VERSION_LIMITATIONS[version])
    header['version'] = version

    header['tiles'], pos = binfile.read_tile_defs(data, pos)

    if version == 0:  # B41
        pos += 1  # skip 0x00
    header['width'], pos = util.read_uint32(data, pos)
    header['height'], pos = util.read_uint32(data, pos)

    if header['version'] == 0:  # B41
        minlayer = 0
        maxlayer, pos = util.read_int32(data, pos)
    else:
        minlayer, pos = util.read_int32(data, pos)
        maxlayer, pos = util.read_int32(data, pos)
        maxlayer += 1

    minlayer = max(minlayer, header['MIN_LAYER'])
    maxlayer = min(maxlayer, header['MAX_LAYER'])
    header['minlayer'] = minlayer
    header['maxlayer'] = maxlayer

    header['rooms'], pos = binfile.read_rooms(data, pos)
    header['buildings'], pos = binfile.read_buildings(data, pos)
    header['zpop'], pos = read_zpop(data, pos, header['CELL_SIZE_IN_BLOCKS'])
    return header


def print_header(header):
    print('header version: {}'.format(header['version']))
    print('dimention: {}x{}'.format(header['width'], header['height']))
    print('layer: [{}, {})'.format(header['minlayer'], header['maxlayer']))
    print('tile types: {}'.format(len(header['tiles'])))
    print('rooms: {}'.format(len(header['rooms'])))
    print('buildings: {}'.format(len(header['buildings'])))

    rmap = {}
    for room in header['rooms']:
        name = room['name']
        rmap[name] = rmap.get(name, 0) + 1
    for k, v in rmap.items():
        print('  {}: {}'.format(k, v))

    zpop = header['zpop']
    for row in zpop:
        print(' '.join(map(lambda x: '{:02X}'.format(x), row)))

    '''
    for tile in header['tiles']:
        print(tile.decode('utf8'))
    '''


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ lotheader reader')
    parser.add_argument('input', type=str)
    parser.add_argument('x', type=int)
    parser.add_argument('y', type=int)
    args = parser.parse_args()

    header = load_lotheader(args.input, args.x, args.y)
    print_header(header)
    print(get_version_info(args.input, 1))
