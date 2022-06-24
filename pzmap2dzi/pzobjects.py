import lupa
from . import geometry

def isListKeys(keys):
    for key in keys:
        if type(key) is not int:
            return False
    if sum(keys) == (len(keys) * (len(keys) + 1) // 2):
        return True
    return False

def unpackTable(table):
    if lupa.lua_type(table) != 'table':
        return table
    d = dict(table)
    keys = list(d.keys())
    isList = isListKeys(keys)
    if isList:
        output = [None] * len(keys)
        for key in keys:
            output[key - 1] = unpackTable(d[key])
    else:
        output = {}
        for key in keys:
            output[key] = unpackTable(d[key])
    return output

def load_objects_raw(objects_path):
    lua = lupa.LuaRuntime(unpack_returned_tuples=False)
    with open(objects_path, 'r') as f:
        lua.execute(f.read())
    olist = unpackTable(lua.globals().objects)
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
def load_foraging_raw(objects_path):
    objects = load_objects_raw(objects_path)
    output = []
    for o in objects:
        if o['type'] in FORAGING_TYPES:
            output.append(o)
    return output

class Obj(object):
    def __init__(self, obj):
        self.geo_type = obj.get('geometry', 'rect')
        self.type = obj.get('type', '')
        self.id = obj['id']
        self.obj = obj
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

def load_cell_foraging_zones(path):
    objects = load_foraging_raw(path)
    cell_foraging = {}
    for obj in objects:
        if obj['z'] != 0:
            continue
        o = Obj(obj)
        for c in o.cells():
            if c not in cell_foraging:
                cell_foraging[c] = []
            cell_foraging[c].append(o)
    return cell_foraging

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