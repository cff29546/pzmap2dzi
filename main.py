import yaml
import os
from distutils.dir_util import copy_tree
import re
import json

def parse_conf(args):
    with open(args.conf, 'r') as f:
        conf = yaml.safe_load(f.read())
    return conf

def parse_map(args):
    with open(args.map_data, 'r') as f:
        map_data = yaml.safe_load(f.read())
    return map_data

def unpack(args):
    from pzmap2dzi import texture
    conf = parse_conf(args)
    map_data = parse_map(args)
    items = list(map_data['textures'].items()) + list(map_data['maps'].items())
    for name, t in items:
        root = t.get('texture_root')
        path = t.get('texture_path')
        files = t.get('texture_files', [])
        pattern = t.get('texture_file_patterns')
        if root and path:
            tl = texture.TextureLibrary()
            folder = os.path.join(conf[root], path)
            if os.path.isdir(folder):
                for f in files:
                    tl.add_pack(os.path.join(folder, f))
                if pattern:
                    for f in os.listdir(folder):
                        for p in pattern:
                            if re.match(p, f):
                                tl.add_pack(os.path.join(folder, f))
                                break
                if not pattern and not files:
                    for f in os.listdir(folder):
                        if f.endswith('.pack'):
                            tl.add_pack(os.path.join(folder, f))
            output = os.path.join(conf['output_path'], 'texture', name)
            tl.save_all(output, conf['render_conf']['worker_count'])

def render_map(cmd, conf, map_data, map_name, is_base):
    from pzmap2dzi import render
    if cmd not in render.RENDER_CMD:
        print('unspported render cmd: {}'.format(cmd))
        return False
    DZI, Render = render.RENDER_CMD[cmd]
    options = conf['render_conf'].copy()
    map_conf = map_data['maps'][map_name]
    map_root = conf[map_conf['map_root']]
    map_path = map_conf['map_path']
    options['input'] = os.path.join(map_root, map_path)

    # base / base_top
    options['cache_name'] = map_name
    options['texture'] = []
    texture_path = os.path.join(conf['output_path'], 'texture', map_name)
    if os.path.isdir(texture_path):
        options['texture'].append(texture_path)
    for texture in map_conf.get('depend_texutres', []):
        texture_path = os.path.join(conf['output_path'], 'texture', texture)
        if os.path.isdir(texture_path):
            options['texture'].append(texture_path)
    if is_base:
        options['output'] = os.path.join(conf['output_path'], 'html', cmd)
    else:
        options['output'] = os.path.join(conf['output_path'], 'html', 'mod_maps', map_name, cmd)
    if is_base and options.get('use_jpg_for_layer0') and cmd == 'base':
        options['layer0_fmt'] = 'jpg'
    else:
        options['layer0_fmt'] = 'png'

    # room / objects
    options['encoding'] = map_conf['encoding']

    print('render [{}] for map [{}]'.format(cmd, map_name))
    r = Render(**options)
    if hasattr(r, 'update_options'):
        options = r.update_options(options)
    dzi = DZI(options['input'], **options)
    suc = dzi.render_all(r, options['worker_count'], options['break_key'], options['verbose'], options['profile'])
    return suc

def save_mod_map_list(conf):
    mod_maps = os.path.join(conf['output_path'], 'html', 'mod_maps')
    if not os.path.isdir(mod_maps):
        return
    maps = []
    for f in os.listdir(mod_maps):
        if os.path.isdir(os.path.join(mod_maps, f)):
            maps.append(f)
    with open(os.path.join(mod_maps, 'map_list.json'), 'w') as f:
        f.write(json.dumps(maps))

def render(args):
    conf = parse_conf(args)
    map_data = parse_map(args)
    conf['render_conf']['total_layers'] = conf['render_conf']['layers']
    for cmd in args.args:
        # base map
        if conf.get('base_map'):
            if not render_map(cmd, conf, map_data, conf['base_map'], True):
                break
        # mod maps
        if not conf.get('mod_maps'):
            continue
        for map_name in conf['mod_maps']:
            if not render_map(cmd, conf, map_data, map_name, False):
                print('render [{}] for map [{}] error'.format(cmd, map_name))
                save_mod_map_list(conf)
                return
            print('render [{}] for map [{}] done'.format(cmd, map_name))
    save_mod_map_list(conf)

def copy(args):
    conf = parse_conf(args)
    script_path = os.path.dirname(os.path.realpath(__file__))
    src = os.path.join(script_path, 'html')
    dst = os.path.join(conf['output_path'], 'html')
    copy_tree(src, dst)

CMD = {
    'unpack': unpack,
    'render': render,
    'copy': copy,
}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi render')
    parser.add_argument('-c', '--conf', type=str, default='conf.yaml')
    parser.add_argument('-m', '--map-data', type=str, default='map_data.yaml')
    parser.add_argument('cmd', type=str)
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    CMD[args.cmd](args)


