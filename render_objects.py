from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import lotheader, util, mp, pzdzi, geometry, pzobjects
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

SUFFIX = []
def break_long_text(text):
    for s in SUFFIX:
        if text.endswith(s):
            return text[:len(text) - len(s)] + '\n' + s
    l = len(text) // 2
    return text[:l] + '\n' + text[l:]

COLOR_MAP = {
    'ZombiesType': 'red',
    'ParkingStall': 'blue',
    'ZoneStory': 'yellow',
}
DEFAULT_COLOR = 'white'
OBJ_FONT = ImageFont.truetype("arial.ttf", 20)
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

def render_tile(dzi, tx, ty, cell_getter, out_path, save_empty):
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
                border, label = cell_getter(cx, cy)
                if not border:
                    continue
                x = (gx - gx0) * pzdzi.SQR_WIDTH // 2
                y = (gy - gy0) * pzdzi.SQR_HEIGHT // 2

                drawing = []
                if layer in border:
                    if (sx, sy) in border[layer]:
                        for t, flag in border[layer][sx, sy]:
                            color = COLOR_MAP.get(t, DEFAULT_COLOR)
                            drawing.append((render_edge, (color, 3, flag)))
                if layer in label:
                    if (sx, sy) in label[layer]:
                        for t, name in label[layer][sx, sy]:
                            color = COLOR_MAP.get(t, DEFAULT_COLOR)
                            drawing.append((render_text, (name, color, OBJ_FONT)))

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

def obj_work(conf, tiles):
    dzi, cell_getter, out_path, save_empty = conf
    for tx, ty in tiles:
        render_tile(dzi, tx, ty, cell_getter, out_path, save_empty)

def process(args):
    if args.verbose:
        print('processing base level:')
    util.ensure_folder(args.output)
    dzi = pzdzi.IsoDZI(args.input, args.tile_size, args.layers, False)
    dzi.ensure_folders(args.output)
    dzi.save_dzi(args.output, 'png')
    types = set()
    if not args.no_car_spawn:
        types = types.union(pzobjects.PARKING_TYPES)
    if not args.no_zombie:
        types = types.union(pzobjects.ZOMBIE_TYPES)
    if not args.no_story:
        types = types.union(pzobjects.STORY_TYPES)
    objects_path = os.path.join(args.input, 'objects.lua')
    cell_zones = pzobjects.load_cell_zones(objects_path, types)

    skip_cells = dzi.cells - set(cell_zones.keys())
    layer0_path = os.path.join(args.output, 'layer0_files')
    base_level_path = os.path.join(layer0_path, str(dzi.base_level))
    groups = dzi.get_tile_groups(base_level_path, 'png', args.group_level, skip_cells)

    cell_getter = pzobjects.CachedBorderLabelMapGetter(objects_path, types)
    conf = (dzi, cell_getter, args.output, args.save_empty_tile)
    t = mp.Task(obj_work, conf, args.mp)
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
    parser.add_argument('--group-level', type=int, default=-1)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('-nc', '--no-car-spawn', action='store_true')
    parser.add_argument('-nz', '--no-zombie', action='store_true')
    parser.add_argument('-ns', '--no-story', action='store_true')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


