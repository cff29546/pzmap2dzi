import os
from . import lotheader, util

class Cell(object):
    def __init__(self, path, header):
        self.header = header
        self.path = path
        self.x = header['x']
        self.y = header['y']
        data = b''
        with open(path, 'rb') as f:
            data = f.read()
        self.version = 0
        pos = 0
        if data[:4] == b'LOTP': #b42
            self.version, pos = util.read_uint32(data, 4)
        self.init_for_version()
        block_num, pos = util.read_uint32(data, pos)
        self.blocks = []
        for i in range(block_num):
            self.read_block(data, pos + i*8)

    def init_for_version(self):
        if self.version != self.header['version']:
            raise Exception("Inconsistent version: H:{} P:{} path:{}".format(
                            self.header['version'], self.version, self.path))
        self.block_per_cell = self.header['CELL_SIZE_IN_BLOCKS']
        self.block_size = self.header['BLOCK_SIZE_IN_SQUARES']
        self.cell_size = self.block_per_cell * self.block_size
        self.minlayer = self.header['minlayer']
        self.maxlayer = self.header['maxlayer']

    def read_block(self, data, pos):
        pos, _ = util.read_uint32(data, pos)
        size = self.block_size
        sqr_size = size*size
        skip = 0
        block = [None] * (self.maxlayer - self.minlayer)
        valid_tiles = 0
        for z in range(self.minlayer, self.maxlayer):
            if skip >= sqr_size:
                skip -= sqr_size
                continue
            layer = [None] * size
            for x in range(size):
                if skip >= size:
                    skip -= size
                    continue
                row = [None] * size
                for y in range(size):
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
                    row[y] = tiles # drop room here as it is not used
                    valid_tiles += 1
                if row != [None] * size:
                    layer[x] = row
            if layer != [None] * size:
                block[z] = layer
        self.blocks.append(block)

    def get_square(self, subx, suby, layer):
        if layer < self.minlayer or layer >= self.maxlayer:
            return None
        bx, x = divmod(subx, self.block_size)
        by, y = divmod(suby, self.block_size)
        block = self.blocks[bx * self.block_per_cell + by]
        layer = block[layer]
        if not layer:
            return None
        row = layer[x]
        if not row:
            return None
        tiles = row[y]
        if not tiles:
            return None
        return map(lambda t:self.header['tiles'][t], tiles)

def load_cell(path, x, y):
    header = lotheader.load_lotheader(path, x, y)
    if not header:
        return None

    lotpack_name = os.path.join(path, 'world_{}_{}.lotpack'.format(x, y))
    if not os.path.isfile(lotpack_name):
        return None
    return Cell(lotpack_name, header)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ lotpack reader')
    parser.add_argument('path', type=str)
    parser.add_argument('x', type=int)
    parser.add_argument('y', type=int)
    args = parser.parse_args()
    
    cell = load_cell(args.path, args.x, args.y)
    lotheader.print_header(cell.header)
    print(len(cell.blocks))

