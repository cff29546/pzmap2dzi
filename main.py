import sys
import os
import io
from distutils.dir_util import copy_tree
import re
import json
import zipfile
from pzmap2dzi import i18n_util
from pzmap2dzi.i18n_util import load_yaml, update_json


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


def sanitize_folder_name(folder_name):
    # Replace illegal characters with _
    return re.sub(r'(?u)[^-\w.]', '_', folder_name)


def git_info():
    head_path = os.path.join(SCRIPT_PATH, '.git', 'HEAD')
    if os.path.isfile(head_path):
        with io.open(head_path, 'r', encoding='utf8') as f:
            head_data = f.read().strip()
    else:
        head_data = ''
    ref = ''
    commit = ''
    if head_data.startswith('ref:'):
        ref = head_data.split(':', 1)[1].strip()
        if ref:
            ref_path = os.path.join(SCRIPT_PATH, '.git', ref)
            if os.path.isfile(ref_path):
                with io.open(ref_path, 'r', encoding='utf8') as f:
                    commit = f.read().strip()
    else:
        commit = head_data
    return ref, commit


def get_version():
    v = {}
    version_file = os.path.join(SCRIPT_PATH, 'VERSION')
    if os.path.isfile(version_file):
        with io.open(version_file, 'r', encoding='utf8') as f:
            for line in f:
                keys = line.strip().split()
                if keys:
                    version = keys[-1]
                    for key in keys[:-1]:
                        v[key] = version
    v['git_branch'], v['git_commit'] = git_info()
    return v


VERSION = get_version()


def load_path(path):
    if os.path.isfile(path):
        return load_yaml(path)
    data = {}
    if os.path.isdir(path):
        for name in os.listdir(path):
            data.update(load_path(os.path.join(path, name)))
    return data


def set_default(data, dft):
    for key in data:
        for k in dft:
            if k not in data[key]:
                data[key][k] = dft[k]
    return data


def parse_map(conf_path):
    conf = load_yaml(conf_path)
    conf_path = os.path.dirname(conf_path)
    maps = {}
    for map_conf in conf['map_conf']:
        map_conf_path = os.path.join(conf_path, map_conf)
        maps.update(load_path(map_conf_path))
    dft = load_yaml(os.path.join(conf_path, conf['map_conf_default']))
    maps = set_default(maps, dft)
    return conf, maps


def get_map_path(conf_path, name):
    conf, maps = parse_map(conf_path)
    return maps[name]['map_path'].format(**dict(maps[name], **conf))


def get_dep(conf, maps, names):
    dep = set([])
    if conf.get('use_depend_texture_only'):
        used = list(names)  # copy
        while len(used) > 0:
            m = used.pop()
            if m in maps and m not in dep:
                dep.add(m)
                used.extend(maps[m].get('depend', []))
    else:
        dep = set(maps.keys())
    return dep


def unpack(args):
    from pzmap2dzi import texture
    conf, maps = parse_map(args.conf)
    mod_maps = conf['mod_maps'] if conf.get('mod_maps') else []
    dep = get_dep(conf, maps, mod_maps + [conf['base_map'], 'default'])

    for d in dep:
        if maps[d].get('texture', False) is False:
            continue
        path = maps[d]['texture_path'].format(**dict(conf, **maps[d]))
        if os.path.isdir(path):
            output = os.path.join(conf['output_root'], 'texture', d)
            tl = texture.TextureLibrary(texture_path=[output])
            for name in os.listdir(path):
                for pattern in maps[d]['texture_files']:
                    if re.match(pattern, name):
                        tl.add_pack(os.path.join(path, name))
                        break
            tl.save_all(output, conf['render_conf']['worker_count'])
        else:
            print('invalid texture_path: {}'.format(path))


def get_conf(options, name, cmd, key, default):
    value = options.get('{}[{}]({})'.format(key, name, cmd))
    if value:
        return value
    value = options.get('{}({})'.format(key, cmd))
    if value:
        return value
    value = options.get('{}[{}]'.format(key, name))
    if value:
        return value
    value = options.get(key)
    if value:
        return value
    return default


CONF_KEY_PATTERN = re.compile(r'(?P<key>[a-zA-Z0-9_]+?)(?:\[(?P<name>[a-zA-Z0-9_]*?)\])?(?:\((?P<cmd>[a-zA-Z0-9_]*?)\))?$')
def copy_options(src, dst, map_name, cmd):
    if isinstance(src, list):
        return [copy_options(v, None, map_name, cmd) for v in src]
    if not isinstance(src, dict):
        return src
    options = dst if dst is not None else {}
    for raw_key in src:
        m = CONF_KEY_PATTERN.match(raw_key)
        if m:
            key = m.group('key')
            if key not in options:
                value = get_conf(src, map_name, cmd, key, src.get(raw_key))
                if isinstance(value, dict) or isinstance(value, list):
                    value = copy_options(value, None, map_name, cmd)
                options[key] = value
    return options


OPTION_RENAME_MAPPING = {
    'omit_levels': 'skip_level',
}
def rename_options(options):
    for old_key, new_key in OPTION_RENAME_MAPPING.items():
        if old_key in options:
            options[new_key] = options.pop(old_key)
    return options


def render_map(cmd, conf, maps, map_name, map_type=None):
    from pzmap2dzi import render
    if cmd not in render.RENDER_CMD:
        print('unspported render cmd: {}'.format(cmd))
        return False
    DZI, Render = render.RENDER_CMD[cmd]
    options = {
        'render_conf': 'DO_NOT_COPY',
        'map_conf': 'DO_NOT_COPY',
        'mod_maps': 'DO_NOT_COPY',
    }
    copy_options(conf['render_conf'], options, map_name, cmd)
    copy_options(conf, options, map_name, cmd)
    map_conf = maps[map_name]
    map_path = map_conf['map_path'].format(**dict(conf, **map_conf))
    rename_options(options)
    options['input'] = map_path

    # base / base_top
    options['cache_name'] = map_name
    dep = get_dep(conf, maps, [map_name, 'default'])
    options['texture'] = []
    for d in dep:
        texture_path = os.path.join(conf['output_root'], 'texture', d)
        if os.path.isdir(texture_path):
            options['texture'].append(texture_path)
    output_path_parts = [conf['output_root'], 'html', 'map_data']
    if map_type == 'mod':
        output_path_parts += ['mod_maps', map_name]
    if map_type is None and cmd == 'base':
        options['image_fmt_layer0'] = options.get('image_fmt_base_layer0')
    if cmd in ['save', 'save_top']:
        output_path_parts += ['saves', sanitize_folder_name(conf['save_game']), cmd.replace('save', 'base')]
    else:
        output_path_parts += [cmd]
    options['output'] = os.path.join(*output_path_parts)

    # room / objects
    options['encoding'] = map_conf['encoding']

    print('render [{}] for map [{}]'.format(cmd, map_name))
    r = Render(**options)
    if hasattr(r, 'update_options'):
        options = r.update_options(options)
    options['pzmap2dzi_version'] = VERSION.get('pzmap2dzi', 'Unknown')
    options['git_branch'] = VERSION.get('git_branch', '')
    options['git_commit'] = VERSION.get('git_commit', '')
    dzi = DZI(options['input'], **options)
    worker_count = options.get('worker_count', 16)
    break_key = options.get('break_key', '')
    verbose = options.get('verbose', False)
    profile = options.get('profile', False)
    suc = dzi.render_all(r, worker_count, break_key, verbose, profile)
    return suc


def gen_map_list(conf, folder):
    mods = os.path.join(conf['output_root'], 'html', 'map_data', folder)
    if not os.path.isdir(mods):
        return
    maps = []
    for f in os.listdir(mods):
        if os.path.isdir(os.path.join(mods, f)):
            maps.append(f)
    with open(os.path.join(mods, 'map_list.json'), 'w') as f:
        f.write(json.dumps(maps))


def render_save(cmd, conf, maps, map_name, save_game):
    conf['save_game'] = save_game
    return render_map(cmd, conf, maps, map_name, 'save')


def render_saves(cmd, conf, maps, map_name):
    if sys.version_info[0] < 3:
        print('save game render only support python 3.x')
        return
    if not conf.get('save_games'):
        print('no save game specified in conf.yaml')
        return
    if conf['save_games'] == 'all':
        from pzmap2dzi import lotheader
        from pzmap2dzi.render_impl.save import get_save_version, match_version
        from pzmap2dzi.pzdzi import PZDZI
        map_conf = maps[map_name]
        map_path = map_conf['map_path'].format(**dict(conf, **map_conf))
        version_info = lotheader.get_version_info(map_path, True)
        map_version = PZDZI.PZ_VERSION.get(version_info['version'], 'Unknown')
        save_root = os.path.expandvars(conf.get('save_game_root'))
        if not save_root or not os.path.isdir(save_root):
            print('invalid save_game_root: {}'.format(save_root))
            return
        conf['save_games'] = []
        for mode_folder in os.listdir(save_root):
            mode_path = os.path.join(save_root, mode_folder)
            if not os.path.isdir(mode_path):
                continue
            for save_folder in os.listdir(mode_path):
                path = os.path.join(mode_path, save_folder)
                if not os.path.isdir(path):
                    continue
                world_version, _ = get_save_version(path)
                if match_version(map_version, world_version):
                    print('Save game found: v{}: {}'.format(world_version, path))
                    save_game = os.path.join(mode_folder, save_folder)
                    conf['save_games'].append(save_game)
                else:
                    print('Save game skipped: v{}: {}'.format(world_version, path))
    for save_game in conf['save_games']:
        conf['save_game'] = save_game
        if render_save(cmd, conf, maps, map_name, save_game):
            conf['render_conf']['save_game_parser_tag'] = 'local'
        else:
            print('render [{}] for save game [{}] error'.format(cmd, save_game))
    gen_map_list(conf, 'saves')


def render(args):
    conf, maps = parse_map(args.conf)
    for cmd in args.args:
        # base map
        if conf.get('base_map'):
            if cmd in ['save', 'save_top']:
                render_saves(cmd, conf, maps, conf['base_map'])
                continue
            if not render_map(cmd, conf, maps, conf['base_map']):
                break
        # mod maps
        if not conf.get('mod_maps'):
            continue
        for map_name in conf['mod_maps']:
            if not render_map(cmd, conf, maps, map_name, 'mod'):
                print('render [{}] for map [{}] error'.format(cmd, map_name))
                gen_map_list(conf, 'mod_maps')
                return
            print('render [{}] for map [{}] done'.format(cmd, map_name))
    gen_map_list(conf, 'mod_maps')


def unzip(path):
    with zipfile.ZipFile(path, 'r') as z:
        z.extractall(os.path.dirname(path))


def process_i18n(path):
    i18n_util.expand_i18n(os.path.join(path, 'i18n.yaml'))
    i18n_util.yaml_aio_to_json_all(os.path.join(path, 'marks.yaml'))


def deploy(args):
    conf = load_yaml(args.conf)
    script_path = os.path.dirname(os.path.realpath(__file__))
    src = os.path.join(script_path, 'html')
    dst = os.path.join(conf['output_root'], 'html')
    copy_tree(src, dst)
    unzip(os.path.join(dst, 'openseadragon', 'openseadragon.zip'))
    process_i18n(os.path.join(dst, 'pzmap', 'i18n'))

    entry = conf.get('output_entry', 'default')
    route = conf.get('output_route', 'map_data/')
    update_json(os.path.join(dst, 'pzmap_config.json'), {
        'route': {
            entry: route,
        },
        'features': {
            'map': True, # mod maps and save maps
            'grid': True,
            'marker': True,
            'trimmer': True,
            'zombie': True,
            'foraging': True,
            'rooms': True,
            'objects': True,
            'streets': True,
            'coords': True,
        },
        'version': VERSION.get('html', 'unknown'),
        'git_branch': VERSION.get('git_branch', ''),
        'git_commit': VERSION.get('git_commit', ''),
    })


CMD = {
    'deploy': deploy,
    'unpack': unpack,
    'render': render,
}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi render')
    parser.add_argument('-c', '--conf', type=str, default='conf/conf.yaml')
    parser.add_argument('cmd', type=str)
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    CMD[args.cmd](args)
