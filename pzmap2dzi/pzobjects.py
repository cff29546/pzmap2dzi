import slpp
import os
from . import geometry, lotheader
from functools import partial
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache


def load_lua_raw(path):
    if not os.path.isfile(path):
        return []
    with open(path, 'r') as f:
        text = f.read()
    return slpp.slpp.decode('{' + text + '}')


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
BASEMENT_TYPES = set(['Basement'])


def filter_objects_raw(objects, types, zrange=None):
    if zrange:
        zmin, zmax = zrange
    output = []
    for o in objects:
        if zrange:
            if o['z'] >= zmax or o['z'] < zmin:
                continue
        if o['type'] in types:
            output.append(o)
    return output


class Obj(object):
    def __init__(self, obj):
        self.geo_type = obj.get('geometry', 'rect')
        self.type = obj.get('type', '')
        self.obj = obj
        self.valid = True
        self.z = obj['z']
        if self.geo_type == 'rect':
            self.x = obj['x']
            self.y = obj['y']
            self.w = obj['width']
            self.h = obj['height']
        if 'points' in obj:
            self.points = geometry.array2points(obj['points'])
        if self.geo_type == 'polyline':
            if 'lineWidth' in obj:
                self.points = geometry.clip(self.points, obj['lineWidth'])
            else:
                self.vaild = False
        if self.valid and self.geo_type in ['polygon', 'polyline']:
            x1, y1, x2, y2 = geometry.points_bound(self.points)
            x1 = int(x1)
            x2 = int(x2 + 0.5) + 1
            y1 = int(y1)
            y2 = int(y2 + 0.5) + 1
            self.x = x1
            self.w = x2 - x1
            self.y = y1
            self.h = y2 - y1

    def cells(self, cell_size):
        if not self.valid:
            return []
        cxmin = self.x // cell_size
        cxmax = (self.x + self.w - 1) // cell_size
        cymin = self.y // cell_size
        cymax = (self.y + self.h - 1) // cell_size
        output = []
        for cx in range(cxmin, cxmax + 1):
            for cy in range(cymin, cymax + 1):
                output.append((cx, cy))
        return output

    def is_inside(self, x, y):
        if self.geo_type == 'rect':
            if (x >= self.x and x < self.x + self.w and
                y >= self.y and y < self.y + self.h):
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
            m[x, y] = [geometry._MAYBE] * 4
        return geometry.get_border_from_square_map(m)


def cell_map(objects_raw, cell_size):
    m = {}
    for obj in objects_raw:
        o = Obj(obj)
        for c in o.cells(cell_size):
            if c not in m:
                m[c] = []
            m[c].append(o)
    return m


def load_cell_zones(path, cell_size, types, zrange=None):
    objects_raw = load_lua_raw(path)['objects']
    objects_raw = filter_objects_raw(objects_raw, types, zrange)
    return cell_map(objects_raw, cell_size)


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


def square_map(cell_zones, cell_size, cx, cy):
    if (cx, cy) not in cell_zones:
        return None
    m = {}
    for z in cell_zones[cx, cy]:
        for x, y in z.square_list():
            if (x < cx * cell_size or x >= (cx + 1) * cell_size or
                y < cy * cell_size or y >= (cy + 1) * cell_size):
                continue
            if (x, y) not in m:
                m[x, y] = z.type
    return m


class CachedGetter(object):
    def __init__(self, path, types, zrange=None, cache_size=16):
        self.path = path
        map_path = os.path.dirname(path)
        version_info = lotheader.get_version_info(map_path, fast_mode=True)
        self.cell_size = version_info['cell_size']
        self.types = types
        self.zrange = zrange
        self.cache_size = cache_size
        self.getter = None

    def get_cell_zones(self):
        return load_cell_zones(self.path, self.cell_size, self.types, self.zrange)

    def __call__(self, cx, cy):
        if self.getter is None:
            self.build_getter()
        return self.getter(cx, cy)


class CachedSquareMapGetter(CachedGetter):
    def build_getter(self):
        self.cell_zones = self.get_cell_zones()
        getter = partial(square_map, self.cell_zones, self.cell_size)
        self.getter = lru_cache(maxsize=self.cache_size)(getter)


class CachedBorderLabelMapGetter(CachedGetter):
    def build_getter(self):
        self.cell_zones = self.get_cell_zones()
        getter = partial(border_label_map, self.cell_zones)
        self.getter = lru_cache(maxsize=self.cache_size)(getter)
