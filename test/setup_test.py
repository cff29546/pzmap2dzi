import os
import io
import sys
import yaml
sys.path.append('..')
import main
sys.path.append('../scripts')
from gen_example_conf import copy, update_conf

def copy_map(dst, src, cells):
    copy(dst, src, 'objects.lua')
    for x, y in cells:
        copy(dst, src, 'world_{}_{}.lotpack'.format(x, y))
        copy(dst, src, '{}_{}.lotheader'.format(x, y))

def copy_conf(dst, src):
    copy(dst, src, 'conf.yaml')
    copy(dst, src, 'default.txt')
    copy(dst, src, 'vanilla.txt')

def get_map_path(conf_file):
    conf, maps = main.parse_map(conf_file)
    return maps['default']['map_path'].format(**dict(maps['default'], **conf))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi test conf setter')
    parser.add_argument('-c', '--conf', type=str, default='../conf')
    parser.add_argument('-o', '--output', type=str, default='test_output')
    parser.add_argument('case_file', type=str)
    args = parser.parse_args()

    case = {}
    with io.open(args.case_file, 'r', encoding='utf8') as f:
        case = yaml.safe_load(f.read())
    
    conf_path = os.path.join(args.output, 'conf')
    copy_conf(conf_path, args.conf)
    map_path = get_map_path(os.path.join(conf_path, 'conf.yaml'))
    for name, value in case.get('conf', {}).items():
        conf = os.path.join(conf_path, name)
        if os.path.exists(conf):
            update_conf(conf, value)

    if os.path.exists(os.path.join(map_path, '..', 'Echo Creek, KY')):
        version = 'B42'
    else:
        version = 'B41'

    maps = case['maps'][version]
    for name, cells in maps.items():
        copy_map(os.path.join(args.output, name), map_path, cells)
