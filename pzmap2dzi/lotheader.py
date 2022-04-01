from . import util

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
    room['name'] = name.decode('utf8')
    room['layer'], pos = util.read_uint32(data, pos)
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
        x, pos = util.read_int32(data, pos) # relative to cell base
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

def read_zpop(data, pos):
    zpop = []
    for i in range(30):
        line = []
        for j in range(30):
            pop, pos = util.read_uint8(data, pos)
            line.append(pop)
        zpop.append(line)
    return zpop, pos

def load_lotheader(path):
    data = b''
    header = {}
    with open(path, 'rb') as f:
        data = f.read()
    header['path'] = path
    header['version'], pos = util.read_uint32(data, 0)
    tile_name_num , pos = util.read_uint32(data, pos)
    tile_names = []
    for i in range(tile_name_num):
        name, pos = util.read_line(data, pos)
        tile_names.append(name.decode('utf8'))
    header['tiles'] = tile_names

    pos += 1  # skip 0x00
    header['width'], pos = util.read_uint32(data, pos)
    header['height'], pos = util.read_uint32(data, pos)
    header['level'], pos = util.read_uint32(data, pos)

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
    header['zpop'], pos = read_zpop(data, pos)

    return header

def print_header(header):
    print('header version: {}'.format(header['version']))
    print('dimention: {}x{}x{}'.format(header['width'], header['height'], header['level']))
    print('tile types: {}'.format(len(header['tiles'])))
    print('rooms: {}'.format(len(header['rooms'])))
    print('buildings: {}'.format(len(header['buildings'])))

    rmap = {}
    for room in header['rooms']:
         name = room['name']
         rmap[name] = rmap.get(name, 0) + 1
    for k, v in rmap.items():
        print('  {}: {}'.format(k.decode('utf8'), v))

    level = ['  ', '\u2591'*2, '\u2592'*2, '\u2593', '\u2588']
    for y in range(30):
        line = []
        for x in range(30):
            line.append(level[header['zpop'][x][y]//52])
        print(''.join(line))

    '''
    for tile in header['tiles']:
        print(tile.decode('utf8'))
    '''


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ lotheader reader')
    parser.add_argument('input', type=str)
    args = parser.parse_args()
    
    header = load_lotheader(args.input)
    print_header(header)
    
