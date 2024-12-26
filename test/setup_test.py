import os
import io
import sys
import yaml
sys.path.append('..')
import main
sys.path.append('../scripts')
from gen_example_conf import copy, update_conf, update_data

def copy_map(dst, src, cells):
    copy(dst, src, 'objects.lua')
    for x, y in cells:
        copy(dst, src, 'world_{}_{}.lotpack'.format(x, y))
        copy(dst, src, '{}_{}.lotheader'.format(x, y))


def copy_conf(dst, src):
    copy(dst, src, 'conf.yaml')
    copy(dst, src, 'default.txt')
    copy(dst, src, 'vanilla.txt')


def load_case(path, name):
    output = {}
    with io.open(os.path.join(path, name), 'r', encoding='utf8') as f:
        case = yaml.safe_load(f.read())
    for d in case.get('copy', []):
        dep = load_case(path, d)
        update_data(output, dep)
    update_data(output, case)
    return output


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi test conf setter')
    parser.add_argument('-c', '--conf', type=str, default='../conf')
    parser.add_argument('-o', '--output', type=str, default='test_output')
    parser.add_argument('case_file', type=str)
    args = parser.parse_args()

    case_dir = os.path.dirname(args.case_file)
    case_name = os.path.basename(args.case_file)
    case = load_case(case_dir, case_name)
    conf_path = os.path.join(args.output, 'conf')
    conf_yaml = os.path.join(conf_path, 'conf.yaml')
    copy_conf(conf_path, args.conf)
    map_path = case.get('map_source')
    if not map_path:
        map_path = main.get_map_path(conf_yaml, 'default')
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
