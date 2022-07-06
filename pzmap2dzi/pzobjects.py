import lupa
from . import geometry
from functools import partial
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

def is_list_keys(keys):
    for key in keys:
        if type(key) is not int:
            return False
    if sum(keys) == (len(keys) * (len(keys) + 1) // 2):
        return True
    return False

def unpack_lua_table(table):
    if lupa.lua_type(table) != 'table':
        return table
    d = dict(table)
    keys = list(d.keys())
    isList = is_list_keys(keys)
    if isList:
        output = [None] * len(keys)
        for key in keys:
            output[key - 1] = unpack_lua_table(d[key])
    else:
        output = {}
        for key in keys:
            output[key] = unpack_lua_table(d[key])
    return output

def load_objects_raw(objects_path):
    lua = lupa.LuaRuntime(unpack_returned_tuples=False)
    with open(objects_path, 'r') as f:
        lua.execute(f.read())
    olist = unpack_lua_table(lua.globals().objects)
    for i in range(len(olist)):
        olist[i]['id'] = i
    return olist

FORAGING_TYPES = set([
    'Nav',
    'TownZone',
    'TrailerPark',
    'Vegitation',
    'Forest',
    'DeepForest',
    'FarmLand',
    'Farm'
])
PARKING_TYPES = set(['ParkingStall'])
ZOMBIE_TYPES = set(['ZombiesType'])
STORY_TYPES = set(['ZoneStory'])
def filter_objects_raw(objects, types, zlimit=None):
    output = []
    for o in objects:
        if zlimit is not None and o['z'] >= zlimit:
            continue
        if o['type'] in types:
            output.append(o)
    return output

class Obj(object):
    def __init__(self, obj):
        self.geo_type = obj.get('geometry', 'rect')
        self.type = obj.get('type', '')
        self.obj = obj
        self.z = obj['z']
        if self.geo_type == 'rect':
            self.x = obj['x']
            self.y = obj['y']
            self.w = obj['width']
            self.h = obj['height']
        if 'points' in obj:
            self.points = geometry.array2points(obj['points'])
        if self.geo_type == 'polyline':
            self.points = geometry.clip(self.points, obj['lineWidth'])
        if self.geo_type in ['polygon', 'polyline']:
            x1, y1, x2, y2 = geometry.points_bound(self.points)
            x1 = int(x1)
            x2 = int(x2 + 0.5) + 1
            y1 = int(y1)
            y2 = int(y2 + 0.5) + 1
            self.x = x1
            self.w = x2 - x1
            self.y = y1
            self.h = y2 - y1

    def cells(self):
        cxmin = self.x // 300
        cxmax = (self.x + self.w - 1) // 300
        cymin = self.y // 300
        cymax = (self.y + self.h - 1) // 300
        output = []
        for cx in range(cxmin, cxmax + 1):
            for cy in range(cymin, cymax + 1):
                output.append((cx, cy))
        return output

    def is_inside(self, x, y):
        if self.geo_type == 'rect':
            if (x >= self.x and x < self.x + self.w
               and y >= self.y and y < self.y + self.h):
               return True
            return False
        if self.geo_type in ['polygon', 'polyline']:
            return geometry.point_in_polygon(self.points, x + 0.5, y + 0.5)
        return None

    def square_list(self):
        output = []
        for x in range(self.x, self.x + self.w):
            for y in range(self.y, self.y + self.h):
                if self.geo_type == 'rect' or self.is_inside(x, y):
                    output.append((x, y))
        return output

    def label_square(self):
        if self.geo_type == 'rect':
            return self.x, self.y
        sl = self.square_list()
        if len(sl) == 0:
            return self.x, self.y
        lx, ly = sl[0]
        for x, y in sl:
             if geometry.label_order(x, y) < geometry.label_order(lx, ly):
                 lx, ly = x, y
        return lx, ly

    def get_border(self):
        if self.geo_type == 'rect':
            return geometry.rects_border([[self.x, self.y, self.w, self.h]])
        m = {}
        for x, y in self.square_list():
            m[x, y] = [geometry._MAYBE_OUTSIDE] * 4
        return geometry.get_border_from_square_map(m)

def cell_map(objects_raw):
    m = {}
    for obj in objects_raw:
        o = Obj(obj)
        for c in o.cells():
            if c not in m:
                m[c] = []
            m[c].append(o)
    return m

def load_cell_zones(path, types, zlimit=None):
    objects_raw = load_objects_raw(path)
    objects_raw = filter_objects_raw(objects_raw, types, zlimit)
    return cell_map(objects_raw)

def border_label_map(cell_zones, cx, cy):
    if (cx, cy) not in cell_zones:
        return {}, {}
    l_map = {}
    b_map = {}
    for z in cell_zones[cx, cy]:
        if z.z not in l_map:
            l_map[z.z] = {}
        if z.z not in b_map:
            b_map[z.z] = {}
        if z.obj['name'] != '':
            x, y = z.label_square()
            if (x, y) not in l_map[z.z]:
                l_map[z.z][x, y] = []
            l_map[z.z][x, y].append((z.type, z.obj['name']))
        for (x, y), flag in z.get_border():
            if (x, y) not in b_map[z.z]:
                b_map[z.z][x, y] = []
            b_map[z.z][x, y].append((z.type, flag))
    return b_map, l_map

def square_map(cell_zones, cx, cy):
    if (cx, cy) not in cell_zones:
        return None
    m = {}
    for z in cell_zones[cx, cy]:
        for x, y in z.square_list():
            if x < cx * 300 or x >= (cx + 1) * 300 or y < cy * 300 or y >= (cy + 1) * 300:
                continue
            if (x, y) not in m:
                m[x, y] = z.type
    return m 

class CachedSquareMapGetter(object):
    def __init__(self, path, types, zlimit=None):
        self.path = path
        self.types = types
        self.zlimit = zlimit
        self.getter = None

    def build_getter(self):
        self.cell_zones = load_cell_zones(self.path, self.types, self.zlimit)
        getter = partial(square_map, self.cell_zones)
        self.getter = lru_cache(maxsize=64)(getter)

    def __call__(self, cx, cy):
        if self.getter is None:
            self.build_getter()
        return self.getter(cx, cy)

class CachedBorderLabelMapGetter(object):
    def __init__(self, path, types, zlimit=None):
        self.path = path
        self.types = types
        self.zlimit = zlimit
        self.getter = None

    def build_getter(self):
        self.cell_zones = load_cell_zones(self.path, self.types, self.zlimit)
        getter = partial(border_label_map, self.cell_zones)
        self.getter = lru_cache(maxsize=64)(getter)

    def __call__(self, cx, cy):
        if self.getter is None:
            self.build_getter()
        return self.getter(cx, cy)

