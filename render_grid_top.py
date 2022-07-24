from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import lotheader, util, mp, pzdzi

TEXT_COLOR = (0, 255, 0, 128) # lime
TEXT_FONT = None
def render_text(draw, x, y, text, size):
    global TEXT_FONT
    global TEXT_COLOR
    if TEXT_FONT == None:
        TEXT_FONT = ImageFont.truetype("arial.ttf", 80 * size)
    w, h = draw.textsize(text, TEXT_FONT)
    draw.text((x - w // 2, y - h // 2), text, TEXT_COLOR, TEXT_FONT)

def render_grid(cx, cy, square_size, grid_size, cell_text):
    im = Image.new('RGBA', (square_size * 300, square_size * 300))
    draw = ImageDraw.Draw(im)
    if grid_size > 0:
        lines, rem = divmod(300, grid_size)
        size = grid_size * square_size
        for b in range(lines):
            draw.line([b * size, 0, b * size, 300 * square_size], 'lime')
            draw.line([0, b * size, 300 * square_size, b * size], 'lime')
    if cell_text:
        render_text(draw, 150 * square_size, 150 * square_size, '{},{}'.format(cx, cy), square_size)

    return im

def grid_work(conf, tile):
    dzi, in_path, out_path, square_size, grid_size, cell_text = conf
    tx, ty = tile
    cx, cy = dzi.tile2cell(tx, ty)
    
    util.set_wip(out_path, tx, ty)
    im = render_grid(cx, cy, square_size, grid_size, cell_text)
    im.save(os.path.join(out_path, '{}_{}.png'.format(tx, ty)))
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

    conf = (dzi, args.input, base_level_path, args.square_size, args.grid_size, args.cell_text)

    t = mp.Task(grid_work, conf, args.mp)
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
    parser.add_argument('-S', '--square-size', type=int, default=4)
    parser.add_argument('-g', '--grid-size', type=int, default=300)
    parser.add_argument('-c', '--cell-text', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


