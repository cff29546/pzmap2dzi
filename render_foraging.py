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

def draw_square(draw, x, y, color):
    h = pzdzi.SQR_HEIGHT // 2
    w = pzdzi.SQR_WIDTH // 2
    draw.polygon([x, y - h, x + w, y, x, y + h, x - w, y], fill=color)

def render_foraging(dzi, tx, ty, cell_getter, out_path, save_empty):
    util.set_wip(out_path, tx, ty)
    gx0, gy0 = dzi.tile2grid(tx, ty, 0)
    left, right, top, bottom = dzi.tile_grid_bound(tx, ty, 0)
    im = None
    draw = None
    text = []
    for gy in range(top, bottom + 1 - 6):
        for gx in range(left, right + 1):
            if (gx + gy) & 1:
                continue
            sx = (gx + gy) // 2
            sy = (gy - gx) // 2
            cx = sx // 300
            cy = sy // 300
            if (cx, cy) not in dzi.cells:
                continue
            x = (gx - gx0) * pzdzi.SQR_WIDTH // 2
            y = (gy - gy0) * pzdzi.SQR_HEIGHT // 2

            cell = cell_getter(cx, cy)
            if not cell:
                continue
            zone_type = cell.get((sx, sy), None)

            if zone_type is None:
                continue

            if not im:
                im = Image.new('RGBA', (dzi.tile_size, dzi.tile_size))
                draw = ImageDraw.Draw(im)
            color = FORAGING_COLOR[zone_type]
            draw_square(draw, x, y, color)

    if im:
        im = dzi.crop_tile(im, tx, ty)
    if im and im.getbbox():
        im.save(os.path.join(out_path, '{}_{}.png'.format(tx, ty)))
    elif save_empty:
        util.set_empty(out_path, tx, ty)

    util.clear_wip(out_path, tx, ty)

def foraging_work(conf, tiles):
    dzi, cell_getter, out_path, save_empty = conf
    for tx, ty in tiles:
        render_foraging(dzi, tx, ty, cell_getter, out_path, save_empty)

def process(args):
    if args.verbose:
        print('processing base level:')
    util.ensure_folder(args.output)
    dzi = pzdzi.IsoDZI(args.input, args.tile_size, args.layers, False)
    dzi.ensure_folders(args.output, 1)
    dzi.save_dzi(args.output, 'png', 1)
    layer0_path = os.path.join(args.output, 'layer0_files')
    base_level_path = os.path.join(layer0_path, str(dzi.base_level))
    objects_path = os.path.join(args.input, 'objects.lua')
    cell_zones = pzobjects.load_cell_zones(objects_path, pzobjects.FORAGING_TYPES, 1)
    skip_cells = dzi.cells - set(cell_zones.keys())
    groups = dzi.get_tile_groups(base_level_path, 'png', args.group_level, skip_cells)

    cell_getter = pzobjects.CachedSquareMapGetter(objects_path, pzobjects.FORAGING_TYPES, 1)
    conf = (dzi, cell_getter, base_level_path, args.save_empty_tile)

    t = mp.Task(foraging_work, conf, args.mp)
    if not t.run(groups, args.verbose, args.stop_key):
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
    parser.add_argument('--tile-size', type=int, default=1024)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('--group-level', type=int, default=-1)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


