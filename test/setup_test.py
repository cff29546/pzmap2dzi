import os
import shutil
import yaml

def copy(dst, src, name):
    source = os.path.join(src, name)
    target = os.path.join(dst, name)
    shutil.copy(source, target)

def copy_map(dst, src, cells):
    try:
        os.makedirs(dst)
    except:
        pass
    copy(dst, src, 'objects.lua')
    for x, y in cells:
        copy(dst, src, 'world_{}_{}.lotpack'.format(x, y))
        copy(dst, src, '{}_{}.lotheader'.format(x, y))

if __name__ == '__main__':
    with open('../conf.yaml', 'r') as f:
        conf = yaml.safe_load(f.read())
    with open('../map_data.yaml', 'r') as f:
        map_data = yaml.safe_load(f.read())
    pz_root = conf['pz_root']
    map_path = os.path.join(pz_root, map_data['maps']['default']['map_path'])
    copy_map('test_output/rosewood', map_path, [(27, 38), (27, 39)])
    copy_map('test_output/custom', map_path, [(26, 38), (26, 39)])

