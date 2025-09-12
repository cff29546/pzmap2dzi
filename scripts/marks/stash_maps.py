import os
import sys
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_BASE_DIR, '../..'))
_DEFAULT_CONF = os.path.join(_BASE_DIR, '../../conf/conf.yaml')
import main
from pzmap2dzi.render_impl import common
from pzmap2dzi import lua_util


def get_map_bounds(path):
    map_def_path = os.path.join(path, 'media', 'lua', 'client', 'ISUI', 'Maps', 'ISMapDefinitions.lua')
    pre = 'getTexture = function(path) return nil end\n'
    post = '''
        MapUtils.initDirectoryMapData = function(mapUI, directory) return nil end
        MapUtils.initDefaultStyleV3 = function(mapUI) return nil end
        MapUtils.overlayPaper = function(mapUI) return nil end
        worldMapImage = function(path) return path end
    '''
    env = lua_util.run_lua_file(map_def_path, None, pre, post)
    env.execute('''
        local mapUI = {}
        local API = {}
        result = {}
        mapUI.javaObject = {}
        mapUI.javaObject.getAPIv1 = function(self) return API end
        API.setBoundsInSquares = function(self, x0, y0, x1, y1)
            self.x0 = x0
            self.y0 = y0
            self.x1 = x1
            self.y1 = y1
        end
        for key, value in pairs(LootMaps.Init) do
            value(mapUI)
            result[key] = {API.x0, API.y0, API.x1, API.y1}
        end
    ''')
    map_bounds = lua_util.unpack_lua_table(env.globals()['result'])
    return map_bounds


def get_stash_maps(path):
    stashes = []
    lua_path = os.path.join(path, 'media', 'lua', 'shared')
    stash_desc_path = os.path.join(lua_path, 'StashDescriptions')
    if not os.path.isdir(stash_desc_path):
        return []
    for f in os.listdir(stash_desc_path):
        if f.endswith('.lua') and f != 'StashUtil.lua':
            stash_path = os.path.join(stash_desc_path, f)
            stashes.extend(lua_util.run_and_get_var(stash_path, 'StashDescriptions', work_dir=lua_path))
    return stashes


def get_marks(path):
    marks = []
    bounds = get_map_bounds(path)
    for name, bounds in bounds.items():
        rect = {
            'x': bounds[0],
            'y': bounds[1],
            'width': bounds[2] - bounds[0],
            'height': bounds[3] - bounds[1],
        }
        marks.append({
            'name': name,
            'type': 'area',
            'color': 'orange',
            'layer': 0,
            'passthrough': True,
            'text_position': 'top',
            'rects': [rect],
        })
    stashes = get_stash_maps(path)
    for s in stashes:
        x = s['buildingX']
        y = s['buildingY']
        if x < 128 and y < 128:
            # ignore invalid position
            continue
        marks.append({
            'name': s['name'],
            'type': 'point',
            'layer': 0,
            'color': 'orange',
            'background': 'gold',
            'text_color': 'yellow',
            'passthrough': True,
            'x': x,
            'y': y,
        })
    return marks


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='basement marker')
    parser.add_argument('-c', '--conf', type=str, default=_DEFAULT_CONF)
    parser.add_argument('-o', '--output', type=str, default='./stash_maps.json')
    args = parser.parse_args()

    map_path = main.get_map_path(args.conf, 'default')
    pz_path = os.path.join(map_path, '..', '..', '..')
    marks = get_marks(pz_path)

    if args.output:
        common.dump_marks(marks, args.output)
        print('{} mark(s) saved to [{}]'.format(len(marks), args.output))
