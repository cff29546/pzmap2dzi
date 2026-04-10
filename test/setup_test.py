import os
import io
import sys
import yaml
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_BASE_DIR, '..'))
sys.path.append(os.path.join(_BASE_DIR, '../scripts'))
_DEFAULT_CONF = os.path.join(_BASE_DIR, '../conf')
try:
    import main
    from gen_example_conf import copy, update_conf, update_data
    from pzmap2dzi import lotheader
except ImportError:
    raise


def copy_map(dst, src, cells):
    copy(dst, src, 'objects.lua')
    copy(dst, src, 'streets.xml')
    for x, y in cells:
        copy(dst, src, 'world_{}_{}.lotpack'.format(x, y))
        copy(dst, src, '{}_{}.lotheader'.format(x, y))
        src_maps = os.path.join(src, 'maps')
        if os.path.isdir(src_maps):
            dst_maps = os.path.join(dst, 'maps')
            copy(dst_maps, src_maps, 'biomemap_{}_{}.png'.format(x, y))


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


def apply_change(conf_path, changes):
    for name, value in changes.items():
        conf = os.path.join(conf_path, name)
        if os.path.exists(conf):
            update_conf(conf, value)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi test conf setter')
    parser.add_argument('-c', '--conf', type=str, default=_DEFAULT_CONF)
    parser.add_argument('-o', '--output', type=str, default='test_output')
    parser.add_argument('case_file', type=str)
    args = parser.parse_args()

    case_dir = os.path.dirname(args.case_file)
    case_name = os.path.basename(args.case_file)
    case = load_case(case_dir, case_name)
    conf_path = os.path.join(args.output, 'conf')
    conf_yaml = os.path.join(conf_path, 'conf.yaml')
    copy_conf(conf_path, args.conf)

    apply_change(conf_path, case.get('preprocess', {}))
    map_path = main.get_map_path(conf_yaml, 'default')
    version_info = lotheader.get_version_info(map_path, True)
    if version_info and version_info.get('version') == 1:
        version = 'B42'
    else:
        version = 'B41'

    apply_change(conf_path, case.get('conf', {}))
    apply_change(conf_path, case.get('conf', {}).get(version, {}))

    maps = case.get('maps', {}).get(version, {})
    for name, cells in maps.items():
        copy_map(os.path.join(args.output, name), map_path, cells)
