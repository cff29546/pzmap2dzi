from . import util


def get_version(data, pos, magic, default):
    next_pos = pos + len(magic)
    if data[pos: next_pos] == magic:
        return util.read_uint32(data, next_pos)
    elif callable(default):
        return default(data, pos)
    else:
        return default


def read_block(data, pos, block_size, layer_range, data_parser):
    square_per_layer = block_size * block_size
    skip = 0
    minlayer, maxlayer = layer_range
    block_data = [None] * (maxlayer - minlayer)
    for z in range(minlayer, maxlayer):
        if skip >= square_per_layer:
            skip -= square_per_layer
            continue
        layer_data = [None] * block_size
        for x in range(block_size):
            if skip >= block_size:
                skip -= block_size
                continue
            row_data = [None] * block_size
            for y in range(block_size):
                if skip > 0:
                    skip -= 1
                    continue
                count, pos = util.read_int32(data, pos)
                if count == -1:
                    skip, pos = util.read_int32(data, pos)
                    if skip > 0:
                        skip -= 1
                        continue
                if count > 1:
                    row_data[y], pos = data_parser(data, pos, count - 1)
            if row_data != [None] * block_size:
                layer_data[x] = row_data
        if layer_data != [None] * block_size:
            block_data[z] = layer_data
    return block_data, pos


def read_tile_defs(data, pos):
    tile_name_num, pos = util.read_uint32(data, pos)
    tile_names = []
    for i in range(tile_name_num):
        name, pos = util.read_line(data, pos)
        tile_names.append(name.decode('utf8').strip())
    return tile_names, pos


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
        x, pos = util.read_int32(data, pos)  # relative to file base
        y, pos = util.read_int32(data, pos)
        metas.append((meta_type, x, y))
    room['objects'] = metas

    return room, pos


def read_rooms(data, pos):
    room_num, pos = util.read_uint32(data, pos)
    rooms = []
    for i in range(room_num):
        room, pos = read_room(data, pos)
        room['id'] = i
        rooms.append(room)
    return rooms, pos


def read_building(data, pos):
    building = {}
    room_num, pos = util.read_uint32(data, pos)
    building['rooms'] = []
    for i in range(room_num):
        room_id, pos = util.read_uint32(data, pos)
        building['rooms'].append(room_id)
    return building, pos


def read_buildings(data, pos):
    building_num, pos = util.read_uint32(data, pos)
    buildings = []
    for i in range(building_num):
        building, pos = read_building(data, pos)
        building['id'] = i
        buildings.append(building)
    return buildings, pos


def load_pzby(path):
    data = b''
    pzby = {}
    with open(path, 'rb') as f:
        data = f.read()

    pzby['path'] = path
    pzby['version'], pos = get_version(data, 0, b'PZBY', (None, 0))
    if pzby['version'] is None:
        return None

    # header
    pzby['tiles'], pos = read_tile_defs(data, pos)
    pzby['width'], pos = util.read_int32(data, pos)
    pzby['height'], pos = util.read_int32(data, pos)
    pzby['layers'], pos = util.read_int32(data, pos)

    pzby['rooms'], pos = read_rooms(data, pos)
    pzby['buildings'], pos = read_buildings(data, pos)

    # chunks
    block_table = pos
    block_size = 8
    blocks = []
    layer_range = [0, pzby['layers']]
    attributes = []
    for i in range(pzby['width'] * pzby['height']):
        pos, _ = util.read_uint32(data, block_table + i * 8)
        attribute, pos = read_block(
            data, pos, block_size, layer_range, pzby_attributes_parser)
        attributes.append(attribute)
        block, pos = read_block(
            data, pos, block_size, layer_range, pzby_data_parser)
        blocks.append(block)
    pzby['attrib'] = attributes
    pzby['blocks'] = blocks
    return pzby


def pzby_attributes_parser(data, pos, count):
    return util.read_int32(data, pos)


def pzby_data_parser(data, pos, count):
    tiles = []
    for i in range(count):
        tile, pos = util.read_int32(data, pos)
        tiles.append(tile)
    return tiles, pos


def lotpack_data_parser(data, pos, count):
    room, pos = util.read_int32(data, pos)  # drop room id as it is not used
    return pzby_data_parser(data, pos, count)
