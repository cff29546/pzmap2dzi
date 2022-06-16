from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import lotheader, util, mp, pzdzi
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

def load_zpop(path, cx, cy):
    name = os.path.join(path, '{}_{}.lotheader'.format(cx, cy))
    if not os.path.isfile(name):
        return None
    header = lotheader.load_lotheader(name)
    zpop = header['zpop']
    for i in range(30):
        for j in range(30):
            if zpop[i][j] > 0:
                return zpop
    return None

def get_color(zombie, alpha):
    r = g = b = 0
    if zombie >= 128:
        r = (zombie - 128) * 2
        g = 255 - r
    else:
        g = zombie * 2
        b = 255 - g
    return (r, g, b, alpha)

def draw_square(draw, x, y, color):
    h = pzdzi.SQR_HEIGHT // 2
    w = pzdzi.SQR_WIDTH // 2
    draw.polygon([x, y - h, x + w, y, x, y + h, x - w, y], fill=color)

def render_zombie(zpop, square_size):
    im = Image.new('RGBA', (square_size * 300, square_size * 300))
    draw = ImageDraw.Draw(im)
    for x in range(30):
        for y in range(30):
            if zpop[x][y] > 0:
                shape = [x * 10 * square_size, y * 10 * square_size, (x + 1) * 10 * square_size, (y + 1) * 10 * square_size]
                draw.rectangle(shape, fill=get_color(zpop[x][y], 128))
    return im

def zombie_work(conf, tile):
    dzi, in_path, out_path, square_size, save_empty = conf
    tx, ty = tile
    cx, cy = dzi.tile2cell(tx, ty)
    
    zpop = load_zpop(in_path, cx, cy)
    util.set_wip(out_path, tx, ty)
    if zpop is not None:
        im = render_zombie(zpop, square_size)
        im.save(os.path.join(out_path, '{}_{}.png'.format(tx, ty)))
    elif save_empty:
        util.set_empty(out_path, tx, ty)
    util.clear_wip(out_path, tx, ty)
    return True

def process(args):
    if args.verbose:
        print('processing base level:')
    util.ensure_folder(args.output)
    dzi = pzdzi.TopDZI(args.input, args.square_size, args.layers)
    dzi.ensure_folders(args.output, 1)
    dzi.save_dzi(args.output, 'png', 1)
    layer0_path = os.path.join(args.output, 'layer0_files')
    base_level_path = os.path.join(layer0_path, str(dzi.base_level))
    tiles = dzi.get_tiles(base_level_path, 'png')

    conf = (dzi, args.input, base_level_path, args.square_size, args.save_empty_tile)

    t = mp.Task(zombie_work, conf, args.mp)
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
    parser = argparse.ArgumentParser(description='PZ map 2d zombie heatmap render')
    parser.add_argument('-o', '--output', type=str, default='./output/html/zombie_top')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-s', '--square-size', type=int, default=4)
    parser.add_argument('--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


