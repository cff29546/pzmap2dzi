import os
import sys
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_BASE_DIR, '../..'))
_DEFAULT_CONF = os.path.join(_BASE_DIR, '../../conf/conf.yaml')
try:
    import main
    from pzmap2dzi import pzobjects
    from pzmap2dzi.render_impl import common
except ImportError:
    raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='basement entry marker')
    parser.add_argument('-c', '--conf', type=str, default=_DEFAULT_CONF)
    parser.add_argument('-o', '--output', type=str, default='./basement.json')
    args = parser.parse_args()

    map_path = main.get_map_path(args.conf, 'default')
    objects_path = os.path.join(map_path, 'objects.lua')
    basements = pzobjects.load_typed_objects(objects_path, set(['Basement']))

    marks = []
    for i, b in enumerate(basements):
        x = b['x'] + b['properties']['StairX']
        y = b['y'] + b['properties']['StairY']
        z = b['z']
        d = b['properties']['StairDirection']
        mark = {'x': x, 'y': y, 'layer': z,
                'type': 'point', 'name': 'Random Basement',
                'desc': 'Stair Direction: ' + d}
        marks.append(mark)

    if args.output:
        common.dump_marks(marks, args.output)
        print('{} mark(s) saved to [{}]'.format(len(marks), args.output))
