import os
import sys
sys.path.append('../..')
import main
from pzmap2dzi import pzobjects
from pzmap2dzi.render_impl import common


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='basement marker')
    parser.add_argument('-c', '--conf', type=str, default='../../conf/conf.yaml')
    parser.add_argument('-o', '--output', type=str, default='basement.json')
    args = parser.parse_args()

    map_path = main.get_map_path(args.conf, 'default')
    objects_path = os.path.join(map_path, 'objects.lua')
    objects = pzobjects.load_lua_raw(objects_path)['objects']
    basements = pzobjects.filter_objects_raw(objects, set(['Basement']))

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

    common.dump_marks(marks, args.output)



