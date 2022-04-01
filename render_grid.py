from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import util, mp, pzdzi

CELL_COLOR = (255, 255, 0, 255) # yellow
BLOCK_COLOR = (0, 255, 0, 255) # green
CELL_FONT = ImageFont.truetype("arial.ttf", 40)
BLOCK_FONT = ImageFont.truetype("arial.ttf", 20)
def render_text(draw, x, y, text, color, font):
    w, h = draw.textsize(text, font)
    draw.text((x - w // 2, y - h // 2), text, color, font)

def render_gridx(draw, x, y, color, width):
    xl, yl = x - pzdzi.SQR_WIDTH // 2, y
    xt, yt = x, y - pzdzi.SQR_HEIGHT // 2
    draw.line([xl, yl, xt, yt], fill=color, width=width)

def render_gridy(draw, x, y, color, width):
    xt, yt = x, y - pzdzi.SQR_HEIGHT // 2
    xr, yr = x + pzdzi.SQR_WIDTH // 2, y
    draw.line([xt, yt, xr, yr], fill=color, width=width)

def render_grid(dzi, tx, ty, out_path, cell_grid, block_grid, save_empty):
    util.set_wip(out_path, tx, ty)
    gx0, gy0 = dzi.tile2grid(tx, ty, 0)
    left, right, top, bottom = dzi.tile_grid_bound(tx, ty, 0)
    im = None
    draw = None
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


            drawing = []
            if cell_grid and sx % 300 == 0:
                drawing.append((render_gridx, (CELL_COLOR, 5)))
            elif block_grid and sx % 10 == 0:
                drawing.append((render_gridx, (BLOCK_COLOR, 1)))
            if cell_grid and sy % 300 == 0:
                drawing.append((render_gridy, (CELL_COLOR, 5)))
            elif block_grid and sy % 10 == 0:
                drawing.append((render_gridy, (BLOCK_COLOR, 1)))
            if cell_grid and sx % 300 == 1 and sy % 300 == 1:
                drawing.append((render_text, ('{},{}'.format(sx // 300, sy // 300), CELL_COLOR, CELL_FONT)))
            if block_grid and sx % 10 == 0 and sy % 10 == 0:
                drawing.append((render_text, ('{},{}'.format(sx // 10, sy // 10), BLOCK_COLOR, BLOCK_FONT)))
            if drawing:
                if not im:
                    im = Image.new('RGBA', (dzi.tile_size, dzi.tile_size))
                    draw = ImageDraw.Draw(im)
                for func, args in drawing:
                    func(draw, x, y, *args)

    if im:
        im = dzi.crop_tile(im, tx, ty)
    if im and im.getbbox():
        im.save(os.path.join(out_path, '{}_{}.png'.format(tx, ty)))
    elif save_empty:
        util.set_empty(out_path, tx, ty)

    util.clear_wip(out_path, tx, ty)

def grid_work(conf, tiles):
    dzi, out_path, cell_grid, block_grid, save_empty = conf
    for tx, ty in tiles:
        render_grid(dzi, tx, ty, out_path, cell_grid, block_grid, save_empty)

def process(args):
    if args.verbose:
        print('processing base level:')
    util.ensure_folder(args.output)
    dzi = pzdzi.DZI(args.input, args.tile_size, args.layers, False)
    dzi.ensure_folders(args.output, 1)
    dzi.save_dzi(args.output, 1)
    layer0_path = os.path.join(args.output, 'layer0_files')
    base_level_path = os.path.join(layer0_path, str(dzi.base_level))
    groups = dzi.get_tile_groups(base_level_path, args.group_size)

    conf = (dzi, base_level_path, args.cell_grid, args.block_grid, args.save_empty_tile)

    t = mp.Task(grid_work, conf, args.mp)
    if not t.run(groups, args.verbose, args.stop_key):
        return False
    if args.verbose:
        print('base level done')

    if args.verbose:
        print('processing pyramid:')
    if not dzi.merge_all_levels(layer0_path, args.mp, args.verbose, args.stop_key):
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ map grid render')
    parser.add_argument('-o', '--output', type=str, default='./output/html/grid')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('--tile-size', type=int, default=1024)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('--group-size', type=int, default=0)
    parser.add_argument('-c', '--cell-grid', action='store_true')
    parser.add_argument('-b', '--block-grid', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


