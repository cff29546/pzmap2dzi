import os
import sys
sys.path.append('../..')
import main
from pzmap2dzi import pzobjects, i18n_util
import json


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='basement marker')
    parser.add_argument('-c', '--conf', type=str, default='../../conf/conf.yaml')
    parser.add_argument('-o', '--output', type=str, default='basement.json')
    args = parser.parse_args()

    map_path = main.get_map_path(args.conf, 'default')
    objects_path = os.path.join(map_path, 'objects.lua')
    objects = pzobjects.load_lua_raw(objects_path)['objects']
    basements = pzobjects.filter_objects_raw(objects, pzobjects.BASEMENT_TYPES)

    marks = []
    for i, b in enumerate(basements):
        x = b['x'] + b['properties']['StairX']
        y = b['y'] + b['properties']['StairY']
        z = b['z']
        d = b['properties']['StairDirection']
        mark = {'x': x, 'y': y, 'layer': z, 'id': str(i),
                'type': 'point', 'name': 'Random Basement',
                'rank': 0, 'desc': 'Stair Direction: ' + d}

        marks.append(mark)

    i18n_util.save_json(args.output, marks)




