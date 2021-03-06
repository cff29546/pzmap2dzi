from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import lotheader, util, mp, pzdzi, geometry
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

class CellRoom(object):
    def __init__(self, rooms):
        self.name = []
        self.edge = {}
        self.label = {}
        for i, r in enumerate(rooms):
            layer = r['layer']
            self.name.append(r['name'])
            edge = geometry.rects_border(r['rects'])
            lx, ly = geometry.label_square(r['rects'])
            self.label[layer, lx, ly] = r['name']

            for (x, y), flag in edge:
                self.edge[layer, x, y] = (i, flag)

@lru_cache(maxsize=128)
def load_cell_room(path, cx, cy):
    name = os.path.join(path, '{}_{}.lotheader'.format(cx, cy))
    if not os.path.isfile(name):
        return None
    header = lotheader.load_lotheader(name)
    if len(header['rooms']) == 0:
        return None
    return CellRoom(header['rooms'])


SUFFIX = [
    'store',
    'storage',
    'kitchen',
    'bathroom',
    'room',
    'rooms',
    'factory',
    'occupied',
    'dining',
    'warehouse',
    'restaurant',
    'clothes',
    'station',
    'game',
    'stand',
    'shipping',
    'cooking',
    'office',
    'print',
    'bottling',
]
def break_long_text(text):
    for s in SUFFIX:
        if text.endswith(s):
            return text[:len(text) - len(s)] + '\n' + s
    l = len(text) // 2
    return text[:l] + '\n' + text[l:]

COLOR_MAP = {
    # DumbBell/BarBell
    'gym': 'lime',

    # Sledgehammer
    'garagestorage': 'orange',   # 60 crate 100 locker 20 shelves,counter
    'storage': 'orange',
    'garage': 'orange',
    'warehouse': 'orange',
    'closet': 'orange',
    'construction': 'orange',
    'factory': 'orange',
    'firestorage': 'orange',
    'shed': 'orange',

    'pawnshop': 'orange',        # 100 crate 10 other
    'pawnshopstorage': 'orange',

    'toolstore': 'magenta',      # 100 shelves 20 other
    'storageunit': 'magenta',    # 60
    'farmstorage': 'magenta',    # 40
    'loggingfactory': 'magenta', # 20 crate 100 shelves
    'toolstorage': 'blue',       # 20
    #'kitchen': 'blue',           # 10, only in crate

    # empty
    'empty': 'silver',
    'emptyoutside': 'silver',
}
DEFAULT_COLOR = 'cyan'
ROOM_FONT = ImageFont.truetype("arial.ttf", 20)
def render_text(draw, x, y, text, color, font):
    w, h = draw.textsize(text, font)
    if w >= pzdzi.SQR_WIDTH:
        text = break_long_text(text)
        w, h = draw.textsize(text, font)
    #draw.rectangle([x - w // 2, y - h // 2, x + w // 2, y + h // 2], fill=(0, 0, 0, 0))
    draw.text((x - w // 2, y - h // 2), text, color, font, align='center')

_PAD_Y = 5
_PAD_X = 10
_WIDTH  = pzdzi.SQR_WIDTH // 2
_HEIGHT = pzdzi.SQR_HEIGHT // 2
def render_edge(draw, x, y, color, width, border_flags):
    edges = geometry.get_edge_segments(border_flags, x, y, _WIDTH, _HEIGHT, _PAD_X, _PAD_Y)
    for edge in edges:
        draw.line(edge, fill=color, width=width)

def render_tile(dzi, tx, ty, in_path, out_path, save_empty):
    flag_path = os.path.join(out_path, 'layer0_files', str(dzi.base_level))
    util.set_wip(flag_path, tx, ty)
    for layer in range(dzi.layers):
        gx0, gy0 = dzi.tile2grid(tx, ty, layer)
        left, right, top, bottom = dzi.tile_grid_bound(tx, ty, layer)
        im = None
        draw = None
        layer_output = os.path.join(out_path, 'layer{}_files'.format(layer), str(dzi.base_level))
        for gy in range(top, bottom + 1 - 6):
            for gx in range(left, right + 1):
                if (gx + gy) & 1:
                    continue
                sx = (gx + gy) // 2
                sy = (gy - gx) // 2
                cx, subx = divmod(sx, 300)
                cy, suby = divmod(sy, 300)
                if (cx, cy) not in dzi.cells:
                    continue
                cell = load_cell_room(in_path, cx, cy)
                if not cell:
                    continue
                x = (gx - gx0) * pzdzi.SQR_WIDTH // 2
                y = (gy - gy0) * pzdzi.SQR_HEIGHT // 2

                drawing = []
                if (layer, subx, suby) in cell.label:
                    name = cell.label[layer, subx, suby]
                    color = COLOR_MAP.get(name, DEFAULT_COLOR)
                    drawing.append((render_text, (name, color, ROOM_FONT)))
                if (layer, subx, suby) in cell.edge:
                    idx, flag = cell.edge[layer, subx, suby]
                    name = cell.name[idx]
                    color = COLOR_MAP.get(name, DEFAULT_COLOR)
                    drawing.append((render_edge, (color, 3, flag)))

                if drawing:
                    if not im:
                        im = Image.new('RGBA', (dzi.tile_size, dzi.tile_size))
                        draw = ImageDraw.Draw(im)
                    for func, args in drawing:
                        func(draw, x, y, *args)
        if im:
            im = dzi.crop_tile(im, tx, ty)
        if im and im.getbbox():
            im.save(os.path.join(layer_output, '{}_{}.png'.format(tx, ty)))
        elif layer == 0 and save_empty:
            util.set_empty(layer_output, tx, ty)
    util.clear_wip(flag_path, tx, ty)
    return True

def room_work(conf, tiles):
    dzi, in_path, out_path, save_empty = conf
    for tx, ty in tiles:
        render_tile(dzi, tx, ty, in_path, out_path, save_empty)

def process(args):
    util.ensure_folder(args.output)

    if args.verbose:
        print('processing base level:')
    dzi = pzdzi.IsoDZI(args.input, args.tile_size, args.layers, False)
    dzi.ensure_folders(args.output)
    dzi.save_dzi(args.output, 'png')
    skip_cells = set()
    for x, y in dzi.cells:
        if not load_cell_room(args.input, x, y):
            skip_cells.add((x, y))
    layer0_path = os.path.join(args.output, 'layer0_files', str(dzi.base_level))
    groups = dzi.get_tile_groups(layer0_path, 'png', args.group_size, skip_cells)

    conf = (dzi, args.input, args.output, args.save_empty_tile)
    t = mp.Task(room_work, conf, args.mp)
    if not t.run(groups, args.verbose, args.stop_key):
        return False

    if args.verbose:
        print('base done')
    
    for layer in range(dzi.layers):
        if args.verbose:
            print('processing layer {} pyramid:'.format(layer))
        path = os.path.join(args.output, 'layer{}_files'.format(layer))
        if not dzi.merge_all_levels(path, 'png', args.mp, args.verbose, args.stop_key):
            return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ map room render')
    parser.add_argument('-o', '--output', type=str, default='./output/html/room')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('--tile-size', type=int, default=1024)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('--group-size', type=int, default=0)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


