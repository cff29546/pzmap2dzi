import os
import io
import yaml
import datetime
import get_mod_dep

def load_yaml(path):
    with io.open(path, 'r', encoding='utf8') as f:
        data = yaml.safe_load(f.read())
    return data

def get_depend(maps, textures):
    id2mod = {}
    mod2id = {}
    for mod_id, t in maps + textures:
        id2mod[t['steam_id']] = mod_id
        mod2id[mod_id] = t['steam_id']
    output = []
    for mod_id, m in maps:
        title, dep = get_mod_dep.get_title_dep(m['steam_id'])
        if title:
            m['display_name'] = title
        if dep:
            m['depend'] = []
            for steam_id, name in dep:
                if steam_id in id2mod:
                    m['depend'].append(id2mod[steam_id])
                else:
                    print('{} depend by {} is not a texture or map mod.'.format((steam_id, name), mod_id))
        output.append((mod_id, m))
        if 'depend' in m:
            print(mod_id, m['depend'])
    return output

def read_info(path):
    info = {}
    with open(path, 'r') as f:
        for line in f:
            kv = line.strip().split('=', 1)
            if len(kv) == 2:
                k, v = kv
                info[k] = v
    return info

def has_texture(path):
    if not os.path.isdir(path):
        return False
    for f in os.listdir(path):
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

def get_steam_conf(mod_root, steam_id):
    conf = {}
    mod_path = os.path.join(mod_root, steam_id, 'mods')
    for mod_name in os.listdir(mod_path):
        mod = {
                'mod_name': mod_name,
                'steam_id': steam_id,
        }
        mod_info = os.path.join(mod_path, mod_name, 'mod.info')
        if os.path.isfile(mod_info):
            info = read_info(mod_info)
            if 'id' in info:
                mod['mod_id'] = info['id']
            if 'name' in info:
                mod['dispaly_name'] = info['name']
        if 'mod_id' not in mod:
            mod['mod_id'] = mod_name
            print('missing mod_id steam_id:{} mod_name:{}'.format(steam_id, mod_name))

        texture_path = os.path.join(mod_path, mod_name, 'media', 'texturepacks')
        if has_texture(texture_path):
            mod['texture'] = True

        map_root = os.path.join(mod_path, mod_name, 'media', 'maps')
        if os.path.isdir(map_root):
            for map_name in os.listdir(map_root):
                map_path = os.path.join(map_root, map_name)
                if is_map(map_path):
                    if 'map_name' in mod:
                        print('multiple maps in single mod steam_id:{} mod_name:{}'.format(steam_id, mod_name))
                        print(map_path)
                    else:
                        mod['map_name'] = map_name

        if mod['mod_id'] in conf:
            print('duplicate mod_id steam_id:{} mod_id:{}'.format(steam_id, mod_id))
        else:
            conf[mod['mod_id']] = mod
    return conf

def collect_info(conf_path):
    with open(conf_path, 'r') as f:
        conf = yaml.safe_load(f.read())
    mod_root = conf['mod_root']
    textures = []
    maps = []
    other = []
    for steam_id in os.listdir(mod_root):
        if not os.path.isdir(os.path.join(mod_root, steam_id)):
            continue
        mods = get_steam_conf(mod_root, steam_id)
        for mod_id in mods:
            if 'map_name' in mods[mod_id]:
                maps.append((mod_id, mods[mod_id]))
                #print('map: {}'.format(mod_id))
            elif 'texture' in mods[mod_id]:
                textures.append((mod_id, mods[mod_id]))
                #print('texture: {}'.format(mod_id))
            else:
                other.append((mod_id, mods[mod_id]))
                #print('other: {}'.format(mod_id))
    print('collecting {} maps mods {} textures mods {} other mods'.format(len(maps), len(textures), len(other)))
    return textures, maps

def output_info(textures, maps, path):
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    texture_file = os.path.join(path, 'textures-{}.txt'.format(timestamp))
    map_file = os.path.join(path, 'maps-{}.txt'.format(timestamp))

    with io.open(texture_file, 'w', encoding='utf8') as f:
        for mod_id, t in textures:
            mod = {'texture': True}
            for key in ['steam_id', 'mod_name']:
                mod[key] = t[key]
            f.write(yaml.safe_dump({mod_id: mod}, encoding=None))
            f.write(u'\n')

    with io.open(map_file, 'w', encoding='utf8') as f:
        for mod_id, m in maps:
            mod = {}
            for key in ['steam_id', 'mod_name', 'map_name', 'display_name', 'depend', 'texture']:
                if key in m and m[key]:
                    mod[key] = m[key]
            f.write(yaml.safe_dump({mod_id: mod}, encoding=None))
            f.write(u'\n')

def update_depend(maps, textures, depends):
    mod_ids = set()
    for mod_id, t in maps + textures:
        mod_ids.add(mod_id)
    depend = {}
    for d in depends:
        depend.update(load_yaml(d))
    for mod_id, mod in maps:
        dep = depend.get(mod_id)
        if dep:
            mod['depend'] = []
            for d in dep.get('depend', []):
                if d in mod_ids:
                    mod['depend'].append(d)
            mod['display_name'] = dep.get('display_name')
    return maps

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='collect mod map info for installed mods')
    parser.add_argument('-c', '--conf', type=str, default='../conf/conf.yaml')
    parser.add_argument('-o', '--output', type=str, default='.')
    parser.add_argument('-g', '--get-depend', action='store_true')
    parser.add_argument('-d', '--depend', action='append', default=[])
    args = parser.parse_args()

    textures, maps = collect_info(args.conf)

    if args.depend:
        maps = update_depend(maps, textures, args.depend)

    if args.get_depend:
        maps = get_depend(maps, textures)

    output_info(textures, maps, args.output)



