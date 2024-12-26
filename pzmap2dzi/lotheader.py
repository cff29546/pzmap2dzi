import os
import re
from . import util

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
        raise Exception('Inconsistent cell_size: {}'.format(cell_size_in_block))
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


def calc_room_bound(room):
    for rect in room['rects']:
        x, y, w, h = rect
        room['xmin'] = min(room.get('xmin', x), x)
        room['xmax'] = max(room.get('xmax', x + w), x + w)
        room['ymin'] = min(room.get('ymin', y), y)
        room['ymax'] = max(room.get('ymax', y + h), y + h)


def read_room(data, pos):
    room = {}
    name, pos = util.read_line(data, pos)
    room['name'] = name
    room['layer'], pos = util.read_int32(data, pos)
    rect_num, pos = util.read_uint32(data, pos)
    rects = []
    room['area'] = 0
    for i in range(rect_num):
        x, pos = util.read_int32(data, pos)
        y, pos = util.read_int32(data, pos)
        w, pos = util.read_int32(data, pos)
        h, pos = util.read_int32(data, pos)
        room['area'] += w * h
        rects.append((x, y, w, h))
    room['rects'] = rects

    calc_room_bound(room)

    meta_num, pos = util.read_uint32(data, pos)
    metas = []
    for i in range(meta_num):
        meta_type, pos = util.read_int32(data, pos)
        x, pos = util.read_int32(data, pos)  # relative to cell base
        y, pos = util.read_int32(data, pos)
        metas.append((meta_type, x, y))
    room['objects'] = metas

    return room, pos


def read_building(data, pos):
    building = {}
    room_num, pos = util.read_uint32(data, pos)
    building['rooms'] = []
    for i in range(room_num):
        room_id, pos = util.read_uint32(data, pos)
        building['rooms'].append(room_id)
    return building, pos


def read_zpop(data, pos, blocks):
    zpop = []
    for i in range(blocks):
        line = []
        for j in range(blocks):
            pop, pos = util.read_uint8(data, pos)
            line.append(pop)
        zpop.append(line)
    return zpop, pos


def get_version(data):
    if data[:4] == b'LOTH':
        return util.read_uint32(data, 4)
    else:
        return util.read_uint32(data, 0)


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

    header['version'], pos = get_version(data)
    header.update(VERSION_LIMITATIONS[header['version']])

    tile_name_num, pos = util.read_uint32(data, pos)
    tile_names = []
    for i in range(tile_name_num):
        name, pos = util.read_line(data, pos)
        tile_names.append(name.decode('utf8'))
    header['tiles'] = tile_names

    if header['version'] == 0:  # B41
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

    room_num, pos = util.read_uint32(data, pos)
    rooms = []
    for i in range(room_num):
        room, pos = read_room(data, pos)
        room['id'] = i
        rooms.append(room)
    header['rooms'] = rooms

    building_num, pos = util.read_uint32(data, pos)
    buildings = []
    for i in range(building_num):
        building, pos = read_building(data, pos)
        building['id'] = i
        buildings.append(building)
    header['buildings'] = buildings
    if header['version'] == 0:  # B41
        header['zpop'], pos = read_zpop(data, pos, 30)
    else:  # B42
        header['zpop'], pos = read_zpop(data, pos, 32)

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
