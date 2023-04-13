
def process(args):
    from pzmap2dzi import render
    if args.cmd not in render.RENDER_CMD:
        print('unspported render cmd: {}'.format(args.cmd))
        return
    DZI, Render = render.RENDER_CMD[args.cmd]
    options = args.__dict__
    r = Render(**options)
    if hasattr(r, 'update_options'):
        options = r.update_options(options)
    dzi = DZI(args.input, **options)
    dzi.render_all(r, args.mp, args.stop_key, args.verbose, args.profile)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi render')
    # dzi config
    parser.add_argument('-o', '--output', type=str, default='./output/html/base')
    parser.add_argument('--tile-size', type=int, default=1024)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('--total-layers', type=int, default=8) # iso dzi
    parser.add_argument('--fmt', type=str, default='png', choices=['png', 'jpg'])
    parser.add_argument('--layer0-fmt', type=str, default='png', choices=['png', 'jpg'])
    parser.add_argument('--skip-level', type=int, default=0)
    parser.add_argument('--compress-level', type=int, default=-1)
    parser.add_argument('--save-empty-tile', action='store_true')
    parser.add_argument('--disable-cache', action='store_true')
    parser.add_argument('--cache-limit-mb', type=int, default=0) # 0 = unlimited
    parser.add_argument('--square-size', type=int, default=1) # top dzi
    # render config
    # base / top base
    parser.add_argument('-t', '--texture', type=str, default='./output/texture')
    parser.add_argument('--season', type=str, default='summer2',
                        choices=['spring', 'summer', 'summer2', 'autumn', 'winter'])
    parser.add_argument('--snow', action='store_true')
    parser.add_argument('--large-bush', action='store_true')
    parser.add_argument('--flower', action='store_true')
    parser.add_argument('--tree-size', type=int, default=2, choices=[0, 1, 2, 3])
    parser.add_argument('--jumbo-tree-size', type=int, default=4,
                        choices=[0, 1, 2, 3, 4, 5]) # also affects dzi
    parser.add_argument('--jumbo-tree-type', type=int, default=0)
    # top base
    parser.add_argument('--top-color-mode', type=str, default='base+water')
    # grid
    parser.add_argument('--cell-grid', action='store_true')
    parser.add_argument('--block-grid', action='store_true')
    # top grid
    parser.add_argument('--grid-gap', type=int, default=300)
    parser.add_argument('--cell-text', action='store_true')
    # room
    parser.add_argument('--encoding', type=str, default='utf8')
    # zombie
    parser.add_argument('--zombie-count', action='store_true')
    # objects
    parser.add_argument('--no-car-spawn', action='store_true')
    parser.add_argument('--no-zombie', action='store_true')
    parser.add_argument('--no-story', action='store_true')

    # main config
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('cmd', type=str)
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)


