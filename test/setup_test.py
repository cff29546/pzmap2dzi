import os
import sys
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

if __name__ == '__main__':
    copy_conf('test_output/conf', '../conf')
    conf, maps = main.parse_map('test_output/conf/conf.yaml')
    map_path = maps['default']['map_path'].format(**dict(maps['default'], **conf))
    update_conf('test_output/conf/vanilla.txt', {
        'default': {'map_path': '{custom_root}/rosewood'},
    })
    update_conf('test_output/conf/custom.txt', {
        'custom': {'map_path': '{custom_root}/custom'},
    })
    update_conf('test_output/conf/conf.yaml', {
        'output_path': '.',
        'map_conf': ['vanilla.txt', 'custom.txt'],
        'use_depend_texture_only': True,
        'mod_maps': ['custom'],
        'render_conf': {
            'enable_cache': True,
            'break_key': '<f9>',
            'image_save_options': {
                'png': {'compress_level': 1},
            },
        },
    })

    if os.path.exists(os.path.join(map_path, '..', 'Echo Creek, KY')): # B42
        copy_map('test_output/rosewood', map_path, [(31, 44), (31, 45)])
        copy_map('test_output/custom', map_path, [(32, 44), (32, 45)])
    else: # B41
        copy_map('test_output/rosewood', map_path, [(27, 38), (27, 39)])
        copy_map('test_output/custom', map_path, [(26, 38), (26, 39)])

