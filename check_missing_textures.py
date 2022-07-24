from __future__ import print_function
import os
from pzmap2dzi import lotheader, texture, util, mp, pzdzi

def process(args):
    cells = util.get_all_cells(args.map_path)
    tl = texture.TextureLibrary(args.texture)
    tl.config_plants(args.season, args.snow, args.flower, args.large_bush,
                  args.tree_size, args.jumbo_tree_size, args.jumbo_tree_type)
    textures = {}
    count = 0
    total = len(cells)
    for x, y in cells:
        if args.verbose:
            count += 1
            print('loading cells {}/{}'.format(count, total), end = '\r')
        
        header_path = os.path.join(args.map_path, '{}_{}.lotheader'.format(x, y))
        header = lotheader.load_lotheader(header_path)
        for tname in header['tiles']:
            if tname in textures:
                textures[tname].append((x, y))
            else:
                textures[tname] = [(x, y)]

    if args.verbose:
        print('')

    count = 0
    total = len(textures)
    for tname in textures:
        if args.verbose:
            count += 1
            print('checking {}/{}'.format(count, total), end = '\r')
        if not tl.get_by_name(tname):
            if args.verbose:
                print('')
            print('{} missing at cells {}'.format(tname, textures[tname]))

    if args.verbose:
        print('\ndone')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='check missing textures')
    parser.add_argument('-t', '--texture', type=str, default='./output/texture')
    parser.add_argument('--season', type=str, default='summer2',
                        choices=['spring', 'summer', 'summer2', 'autumn', 'winter'])
    parser.add_argument('--snow', action='store_true')
    parser.add_argument('--large-bush', action='store_true')
    parser.add_argument('--flower', action='store_true')
    parser.add_argument('--tree-size', type=int, default=2, choices=[0, 1, 2, 3])
    parser.add_argument('--jumbo-tree-size', type=int, default=4, choices=[0, 1, 2, 3, 4, 5])
    parser.add_argument('--jumbo-tree-type', type=int, default=0)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('map_path', type=str)
    args = parser.parse_args()

    process(args)


