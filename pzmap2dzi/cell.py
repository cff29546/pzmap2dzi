import os
import re
from . import lotheader, texture, util

def read_block(data, pos, level):
    next_pos = pos + 8
    pos, _ = util.read_uint32(data, pos)
    level = min(level, 8)
    skip = 0
    block = [None] * level
    valid_tiles = 0
    for l in range(level):
        if skip >= 100:
            skip -= 100
            continue
        lv = [None] * 10
        for x in range(10):
            if skip >= 10:
                skip -= 10
                continue
            row = [None] * 10
            for y in range(10):
                if skip > 0:
                    skip -= 1
                    continue
                count, pos = util.read_int32(data, pos)
                if count == -1:
                    skip, pos = util.read_int32(data, pos)
                    if skip > 0:
                        skip -= 1
                        continue
                if count <= 1:
                    continue
                room, pos = util.read_int32(data, pos)
                tiles = []
                for i in range(count - 1):
                    tile, pos = util.read_int32(data, pos)
                    tiles.append(tile)
                row[y] = {'room': room, 'tiles': tiles}
                valid_tiles += 1
            if row != [None] * 10:
                lv[x] = row
        if lv != [None] * 10:
            block[l] = lv
    return block, next_pos

def load_lotpack(path, header):
    data = b''
    with open(path, 'rb') as f:
        data = f.read()
    block_num, pos = util.read_uint32(data, 0)
    blocks = []
    for i in range(block_num):
        block, pos = read_block(data, pos, header['level'])
        blocks.append(block)
    return blocks

def load_cell(path, x, y):
    lotheader_name = os.path.join(path, '{}_{}.lotheader'.format(x, y))
    lotpack_name = os.path.join(path, 'world_{}_{}.lotpack'.format(x, y))

    if not os.path.isfile(lotheader_name):
        return None
    if not os.path.isfile(lotpack_name):
        return None
    header = lotheader.load_lotheader(lotheader_name)
    blocks = load_lotpack(lotpack_name, header)

    cell = {'header': header, 'blocks': blocks}
    return cell

from PIL import Image
def get_offset(x, y):
    xbase = -9
    ybase = 0

    gx = x - y
    gy = x + y
    return (gx - xbase) * 64, gy * 32

def render_block(map_data, tl, cx, cy):
    im = Image.new('RGBA', (64*20, 32*18 + 256))

    block = map_data['blocks'][cx * 30 + cy]
    for x in range(10):
        for y in range(10):
            ox, oy = get_offset(x, y)
            print('tile {} {}'.format(x, y))
            for t in block[0][x][y]['tiles']:
                name = map_data['header']['tiles'][t]
                print(name)
                texture = tl.get_by_name(name)
                if texture:
                    texture.render(im, ox, oy)
    return im

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ map data reader')
    parser.add_argument('mappath', type=str)
    args = parser.parse_args()
    
    '''
    mapdata = {}
    HEADER_FILE_PATTERN = re.compile('(\\d+)_(\\d+)\\.lotheader')
    import os, win32api, win32con, win32process
    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION|win32con.PROCESS_VM_READ, 0, os.getpid())
    for f in os.listdir(args.mappath):
        m = HEADER_FILE_PATTERN.match(f)
        if not m:
            continue

        x, y = map(int, m.groups())
        #print('Loading {}, {}'.format(x, y))
        mapdata[(x, y)] = load_cell(args.mappath, x, y)
        process_memory = int(win32process.GetProcessMemoryInfo(handle)['WorkingSetSize'])
        mb = process_memory / 1024 / 1024
        print(f'{len(mapdata)} : {mb:.2f} MB       \r', end='')
    os.system('pause')
    '''
