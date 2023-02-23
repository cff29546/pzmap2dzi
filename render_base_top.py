from PIL import Image, ImageDraw, ImageFont
import os
from pzmap2dzi import cell, texture, util, mp, pzdzi

def color_from_sums(color_sums):
    if color_sums:
        r, g, b, n = map(sum, zip(*color_sums))
        color = (r // n, g // n, b // n, 255)
        return color
    return None

def rc_base(tl, tile_names, tile_ids):
    tx = tl.get_by_name(tile_names[tile_ids[0]])
    if tx:
        return color_from_sums([tx.get_color_sum()])
    return None

_half_water = set([
    'blends_natural_02_1',
    'blends_natural_02_2',
    'blends_natural_02_3',
    'blends_natural_02_4',
])
def rc_base_water(tl, tile_names, tile_ids):
    color_sums = []
    for tid in tile_ids:
        name = tile_names[tid]
        tx = tl.get_by_name(name)
        if tx:
            color_sum = tx.get_color_sum()
            if color_sum:
                if len(color_sums) == 0:
                    color_sums.append(color_sum)
                if name in _half_water:
                    color_sums.append(color_sum)
                    break
    return color_from_sums(color_sums)

def rc_avg(tl, tile_names, tile_ids):
    color_sums = []
    for tid in tile_ids:
        name = tile_names[tid]
        tx = tl.get_by_name(name)
        if tx:
            color_sum = tx.get_color_sum()
            if color_sum:
                color_sums.append(color_sum)
    return color_from_sums(color_sums)

_render_func = {
    'base': rc_base,
    'base+water': rc_base_water,
    'avg': rc_avg,
}

def render_cell(tl, cell_data, layer=0, size=1, render_mode='default'):
    im = None
    draw = None
    tile_names = cell_data['header']['tiles']
    render_color = _render_func.get(render_mode, rc_base)
    for bx in range(30):
        for by in range(30):
            block = cell_data['blocks'][bx * 30 + by]
            if block is None or block[layer] is None:
                continue
            for x in range(10):
                if block[layer][x] is None:
                    continue
                for y in range(10):
                    if block[layer][x][y] is None:
                        continue
                    if im is None:
                        im = Image.new('RGBA', (300 * size, 300 * size))
                        draw = ImageDraw.Draw(im)
                    color = render_color(tl, tile_names, block[layer][x][y]['tiles'])
                    if color:
                        px = (bx * 10 + x) * size
                        py = (by * 10 + y) * size
                        draw.rectangle([px, py, px + size - 1, py + size - 1], fill=color)

    return im

def base_work(conf, tile):
    dzi, texture_lib, in_path, out_path, ext0, square_size, render_mode = conf
    tx, ty = tile
    cx, cy = dzi.tile2cell(tx, ty)
    
    data = cell.load_cell(in_path, cx, cy)
    flag_path = os.path.join(out_path, 'layer0_files', str(dzi.base_level))
    util.set_wip(flag_path, tx, ty)
    for layer in range(dzi.layers):
        im = render_cell(texture_lib, data, layer, square_size, render_mode)
        if im is not None and im.getbbox():
            layer_output = os.path.join(out_path, 'layer{}_files'.format(layer), str(dzi.base_level))
            ext = ext0 if layer == 0 else 'png'
            if ext == 'jpg':
                im = im.convert('RGB')
            im.save(os.path.join(layer_output, '{}_{}.{}'.format(tx, ty, ext)))
    util.clear_wip(flag_path, tx, ty)
    return True

def process(args):
    texture_lib = texture.TextureLibrary(args.texture)
    texture_lib.config_plants(args.season, args.snow, args.flower, args.large_bush,
                              args.tree_size, args.jumbo_tree_size, args.jumbo_tree_type)
    util.ensure_folder(args.output)

    if args.verbose:
        print('processing base level:')
    dzi = pzdzi.TopDZI(args.input, args.square_size, args.layers)
    dzi.ensure_folders(args.output)
    dzi.save_dzi(args.output, 'png')
    if args.layer0_fmt != 'png':
        dzi.save_dzi(args.output, args.layer0_fmt, 1)
    layer0_path = os.path.join(args.output, 'layer0_files', str(dzi.base_level))
    tiles = dzi.get_tiles(layer0_path, args.layer0_fmt)

    conf = (dzi, texture_lib, args.input, args.output, args.layer0_fmt, args.square_size, args.render_mode)

    t = mp.Task(base_work, conf, args.mp)
    if not t.run(tiles, args.verbose, args.stop_key):
        return False
    if args.verbose:
        print('base done')

    for layer in range(dzi.layers):
        if args.verbose:
            print('processing layer {} pyramid:'.format(layer))
        path = os.path.join(args.output, 'layer{}_files'.format(layer))
        ext = args.layer0_fmt if layer == 0 else 'png'
        if not dzi.merge_all_levels(path, ext, args.mp, args.verbose, args.stop_key):
            return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ map top view base render')
    parser.add_argument('-o', '--output', type=str, default='./test_output/html/base_top')
    parser.add_argument('-t', '--texture', type=str, default='./test_output/texture')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('--season', type=str, default='summer2',
                        choices=['spring', 'summer', 'summer2', 'autumn', 'winter'])
    parser.add_argument('--snow', action='store_true')
    parser.add_argument('--large-bush', action='store_true')
    parser.add_argument('--flower', action='store_true')
    parser.add_argument('--tree-size', type=int, default=2, choices=[0, 1, 2, 3])
    parser.add_argument('--jumbo-tree-size', type=int, default=4, choices=[0, 1, 2, 3, 4, 5])
    parser.add_argument('--jumbo-tree-type', type=int, default=0)
    parser.add_argument('-S', '--square-size', type=int, default=4)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('--layer0-fmt', type=str, default='png', choices=['png', 'jpg'])
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-r', '--render-mode', type=str, default='base+water')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('input', type=str)
    #parser.add_argument('x', type=int)
    #parser.add_argument('y', type=int)
    args = parser.parse_args()

    process(args)


