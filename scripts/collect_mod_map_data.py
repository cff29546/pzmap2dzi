import os
import yaml

DEFAULT_MAP = '''
    default:
        map_root: pz_root
        map_path: |- # map path from map root
            media\\maps\\Muldraugh, KY
        encoding: utf8
        texture_root: pz_root
        texture_path: |- # texture path from textrue root
            media\\texturepacks
        texture_files:
            - Erosion.pack
            - ApCom.pack
            - RadioIcons.pack
            - ApComUI.pack
            - JumboTrees2x.pack
            - Tiles2x.floor.pack
            - Tiles2x.pack
'''

TEXTURE_TEMPLATE = '''
        texture_root: mod_root
        texture_path: |-
            {}
        texture_file_patterns: ['.*[.]pack']'''

MAP_TEMPLATE = '''
        map_root: mod_root
        map_path: |-
            {}
        encoding: utf8
        depend_texutres:
            - default'''



def has_texture(tpath):
    if not os.path.isdir(tpath):
        return False
    for f in os.listdir(tpath):
        if f.endswith('.pack'):
            return True
    return False

def is_map(mpath):
    if not os.path.isdir(mpath):
        return False
    for f in os.listdir(mpath):
        if f.endswith('.lotheader'):
            return True
    return False

def get_mod_conf(mod_root, mod_id):
    conf = {}
    mod_path = os.path.join(mod_root, mod_id, 'mods')
    for name in os.listdir(mod_path):
        mod = {}
        tpath = os.path.join(mod_id, 'mods', name, 'media', 'texturepacks')
        if has_texture(os.path.join(mod_root, tpath)):
            mod['texture'] = tpath
        map_root = os.path.join(mod_path, name, 'media', 'maps')
        if os.path.isdir(map_root):
            for map_name in os.listdir(map_root):
                mpath = os.path.join(mod_id, 'mods', name, 'media', 'maps', map_name)
                if is_map(os.path.join(mod_root, mpath)):
                    if 'map' in mod:
                        print('multiple maps in single mod:')
                        print(mpath)
                    else:
                        mod['map'] = mpath
        conf[name] = mod
    return conf

if __name__ == '__main__':
    with open('../conf.yaml', 'r') as f:
        conf = yaml.safe_load(f.read())
    mod_root = conf['mod_root']
    textures = []
    maps = []
    for mod_id in os.listdir(mod_root):
        if not os.path.isdir(os.path.join(mod_root, mod_id)):
            continue
        mods = get_mod_conf(mod_root, mod_id)
        for name in mods:
            if 'map' in mods[name]:
                maps.append((name, mods[name]))
            elif 'texture' in mods[name]:
                textures.append((name, mods[name]))
    
    with open('map_data.yaml', 'w') as f:
        f.write('textures:\n')
        for name, t in textures:
            f.write('    {}:'.format(name))
            f.write(TEXTURE_TEMPLATE.format(t['texture']))
            f.write('\n\n')
        f.write('maps:' + DEFAULT_MAP)
        for name, m in maps:
            f.write('    {}:'.format(name))
            f.write(MAP_TEMPLATE.format(m['map']))
            if 'texture' in m:
                f.write(TEXTURE_TEMPLATE.format(m['texture']))
            f.write('\n\n')




