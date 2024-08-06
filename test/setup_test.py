import os
import shutil
import yaml
import sys
sys.path.append('..')
import main

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
    conf, maps = main.parse_map('../conf/conf.yaml')
    map_path = maps['default']['map_path'].format(**dict(maps['default'], **conf))
    copy_map('test_output/rosewood', map_path, [(27, 38), (27, 39)])
    copy_map('test_output/custom', map_path, [(26, 38), (26, 39)])

