from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import lotheader, util, mp, pzdzi, pzobjects

FORAGING_COLOR = {
    'Nav':         (255, 255, 255, 128),
    'TownZone':    (  0,   0, 255, 128),
    'TrailerPark': (  0, 255, 255, 128),
    'Vegitation':  (255, 255,   0, 128),
    'Forest':      (  0, 255,   0, 128),
    'DeepForest':  (  0, 128,   0, 128),
    'FarmLand':    (255,   0, 255, 128),
    'Farm':        (255,   0,   0, 128),
}

def render_foraging(cell, cx, cy, square_size):
    im = Image.new('RGBA', (square_size * 300, square_size * 300))
    draw = ImageDraw.Draw(im)
    for x in range(300):
        sx = x + cx * 300
        for y in range(300):
            sy = y + cy * 300
            zone_type = cell.get((sx, sy), None)
            if zone_type:
                shape = [x * square_size, y * square_size, (x + 1) * square_size, (y + 1) * square_size]
                draw.rectangle(shape, fill=FORAGING_COLOR[zone_type])
    return im

def foraging_work(conf, tile):
    dzi, cell_getter, out_path, square_size, save_empty = conf
    tx, ty = tile
    cx, cy = dzi.tile2cell(tx, ty)
    
    cell = cell_getter(cx, cy)
    util.set_wip(out_path, tx, ty)
    if cell is not None:
        im = render_foraging(cell, cx, cy, square_size)
        im.save(os.path.join(out_path, '{}_{}.png'.format(tx, ty)))
    elif save_empty:
        util.set_empty(out_path, tx, ty)
    util.clear_wip(out_path, tx, ty)
    return True

    #render_foraging(dzi, tx, ty, cell_getter, out_path, save_empty)

def process(args):
    if args.verbose:
        print('processing base level:')
    util.ensure_folder(args.output)
    dzi = pzdzi.TopDZI(args.input, args.square_size, args.layers)
    dzi.ensure_folders(args.output, 1)
    dzi.save_dzi(args.output, 'png', 1)
    layer0_path = os.path.join(args.output, 'layer0_files')
    base_level_path = os.path.join(layer0_path, str(dzi.base_level))
    objects_path = os.path.join(args.input, 'objects.lua')
    cell_zones = pzobjects.load_cell_zones(objects_path, pzobjects.FORAGING_TYPES, 1)
    skip_cells = dzi.cells - set(cell_zones.keys())
    tiles = dzi.get_tiles(base_level_path, 'png')

    cell_getter = pzobjects.CachedSquareMapGetter(objects_path, pzobjects.FORAGING_TYPES, 1)
    conf = (dzi, cell_getter, base_level_path, args.square_size, args.save_empty_tile)

    t = mp.Task(foraging_work, conf, args.mp)
    if not t.run(tiles, args.verbose, args.stop_key):
        return False
    if args.verbose:
        print('base level done')

    if args.verbose:
        print('processing pyramid:')
    if not dzi.merge_all_levels(layer0_path, 'png', args.mp, args.verbose, args.stop_key):
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ map zombie heatmap render')
    parser.add_argument('-o', '--output', type=str, default='./output/html/zombie')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-S', '--square-size', type=int, default=4)
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


