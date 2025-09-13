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


_ANIMAL_COLORS = {
    'deer': 'brown',
    'rabbit': 'white',
    'predator': 'gray',
    'small': 'orange',
    'large': 'red',
}


def convert_points(p):
    return [{'x': p[i], 'y': p[i+1]} for i in range(0, len(p) - 1, 2)]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='animal tracks marker')
    parser.add_argument('-c', '--conf', type=str, default=_DEFAULT_CONF)
    parser.add_argument('-o', '--output', type=str,
                        default='./animal_tracks.json')
    args = parser.parse_args()

    map_path = main.get_map_path(args.conf, 'default')
    objects_path = os.path.join(map_path, 'objects.lua')
    animals = pzobjects.load_typed_objects(objects_path, set(['Animal']))

    marks = []
    for a in animals:
        properties = a.get('properties', {})
        points = convert_points(a.get('points', []))
        action = properties.get('Action', '')
        animal_type = properties.get('AnimalType', '')
        color = _ANIMAL_COLORS.get(animal_type.lower(), 'blue')
        name = ''
        visible_zoom_level = 0
        if animal_type:
            name = animal_type
        elif action:
            visible_zoom_level = 2
            name = action

        marks.append({
            'type': 'polyline',
            'name': name,
            'layer': 0,
            'passthrough': True,
            'text_position': 'dynamic',
            'visible_zoom_level': visible_zoom_level,
            'color': color,
            'points': points,
        })

    if args.output:
        common.dump_marks(marks, args.output)
        print('{} mark(s) saved to [{}]'.format(len(marks), args.output))
