from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import lotheader, util, mp, pzdzi
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

@lru_cache(maxsize=128)
def load_cell(path, cx, cy):
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

ZOMBIE_FONT = ImageFont.truetype("arial.ttf", 40)
def render_text(draw, x, y, text, color, font):
    w, h = draw.textsize(text, font)
    draw.text((x - w // 2, y - h // 2), text, color, font)

def draw_square(draw, x, y, color):
    h = pzdzi.SQR_HEIGHT // 2
    w = pzdzi.SQR_WIDTH // 2
    draw.polygon([x, y - h, x + w, y, x, y + h, x - w, y], fill=color)

def render_zombie(dzi, tx, ty, in_path, out_path, save_empty, zombie_count):
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
            cx, subx = divmod(sx, 300)
            cy, suby = divmod(sy, 300)
            if (cx, cy) not in dzi.cells:
                continue
            x = (gx - gx0) * pzdzi.SQR_WIDTH // 2
            y = (gy - gy0) * pzdzi.SQR_HEIGHT // 2

            cell = load_cell(in_path, cx, cy)
            if not cell:
                continue
            zpop = cell[subx // 10][suby // 10]

            if zpop == 0:
                continue

            if not im:
                im = Image.new('RGBA', (dzi.tile_size, dzi.tile_size))
                draw = ImageDraw.Draw(im)
            draw_square(draw, x, y, get_color(zpop, 128))

            if zombie_count and subx % 10 == 9 and suby % 10 == 0:
                text.append((x, y, "z:{}".format(zpop), get_color(zpop, 255), ZOMBIE_FONT))
    for args in text:
        render_text(draw, *args)

    if im:
        im = dzi.crop_tile(im, tx, ty)
    if im and im.getbbox():
        im.save(os.path.join(out_path, '{}_{}.png'.format(tx, ty)))
    elif save_empty:
        util.set_empty(out_path, tx, ty)

    util.clear_wip(out_path, tx, ty)

def zombie_work(conf, tiles):
    dzi, in_path, out_path, save_empty, zombie_count = conf
    for tx, ty in tiles:
        render_zombie(dzi, tx, ty, in_path, out_path, save_empty, zombie_count)

def process(args):
    if args.verbose:
        print('processing base level:')
    util.ensure_folder(args.output)
    dzi = pzdzi.IsoDZI(args.input, args.tile_size, args.layers, False)
    dzi.ensure_folders(args.output, 1)
    dzi.save_dzi(args.output, 'png', 1)
    layer0_path = os.path.join(args.output, 'layer0_files')
    base_level_path = os.path.join(layer0_path, str(dzi.base_level))
    groups = dzi.get_tile_groups(base_level_path, 'png', args.group_level)

    conf = (dzi, args.input, base_level_path, args.save_empty_tile, args.zombie_density_value)

    t = mp.Task(zombie_work, conf, args.mp)
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
    parser.add_argument('-z', '--zombie-density-value', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


