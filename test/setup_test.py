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
    for sx, sy, dx, dy in cells:
        copy(dst, src, 'world_{}_{}.lotpack'.format(sx, sy),
             'world_{}_{}.lotpack'.format(dx, dy))
        copy(dst, src, '{}_{}.lotheader'.format(sx, sy),
             '{}_{}.lotheader'.format(dx, dy))
        src_maps = os.path.join(src, 'maps')
        if os.path.isdir(src_maps):
            dst_maps = os.path.join(dst, 'maps')
            copy(dst_maps, src_maps,
                 'biomemap_{}_{}.png'.format(sx, sy),
                 'biomemap_{}_{}.png'.format(dx, dy))


def _parse_coord(value, field_name):
    if (not isinstance(value, (list, tuple))) or len(value) != 2:
        raise ValueError('{} must be [x, y], got {}'.format(field_name, value))
    return int(value[0]), int(value[1])


def _expand_map_items(items):
    output = []
    for item in items:
        if isinstance(item, (list, tuple)):
            x, y = _parse_coord(item, 'cell')
            output.append((x, y, x, y))
            continue

        if not isinstance(item, dict):
            raise ValueError('map item must be [x, y] or dict, got {}'.format(item))

        src = _parse_coord(item.get('src'), 'src')
        has_dst = 'dst' in item
        has_offset = 'offset' in item
        if has_dst and has_offset:
            raise ValueError('dst and offset cannot both be present: {}'.format(item))

        if has_dst:
            dst = _parse_coord(item.get('dst'), 'dst')
        elif has_offset:
            ox, oy = _parse_coord(item.get('offset'), 'offset')
            dst = (src[0] + ox, src[1] + oy)
        else:
            dst = src

        size = item.get('size', [1, 1])
        width, height = _parse_coord(size, 'size')
        if width < 1 or height < 1:
            raise ValueError('size must be [width>=1, height>=1], got {}'.format(size))

        # Expand area with dx in [0, width), dy in [0, height).
        for dx in range(width):
            for dy in range(height):
                output.append((
                    src[0] + dx,
                    src[1] + dy,
                    dst[0] + dx,
                    dst[1] + dy,
                ))
    return output


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
    version_info = lotheader.get_version_info(map_path)
    version = version_info.get('pz_version', 'unknown')

    apply_change(conf_path, case.get('conf', {}))
    apply_change(conf_path, case.get('conf', {}).get(version, {}))

    maps = case.get('maps', {}).get(version, {})
    for name, cells in maps.items():
        expanded_cells = _expand_map_items(cells)
        copy_map(os.path.join(args.output, name), map_path, expanded_cells)
