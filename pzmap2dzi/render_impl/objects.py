from PIL import Image, ImageColor
import os
import struct
import itertools

from pzmap2dzi import pzdzi
from .common import (
    draw_square, render_long_text, render_edge, LazyFont, dump_marks
)
from .. import pzobjects, lua_util

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache


def non_skip_key_set(d):
    kvs = filter(lambda kv: kv[1] != 'skip', d.items())
    return set(map(lambda kv: kv[0], kvs))


class ColorMapper(object):
    def __init__(self, color_map, default_color_name, default_alpha=255):
        self.k2n = color_map
        self.alpha = default_alpha
        self.default_name = default_color_name
        self.default_color = self.resolve_color_name(default_color_name)
        self.k2c = {}
        self.k2i = {}
        self.init()
    
    def init(self, mapping=None):
        if mapping:
            self.i2c = [None] * len(mapping)
            for i, k in enumerate(mapping):
                n = self.k2n.get(k)
                if n is None:
                    continue
                c = self.resolve_color_name(n)
                self.i2c[i] = c
                self.k2c[k] = c
                self.k2i[k] = i
        else:
            self.i2c = [self.default_color]
            for k, n in self.k2n.items():
                c = self.resolve_color_name(n)
                if c in self.i2c:
                    self.k2i[k] = self.i2c.index(c)
                else:
                    self.k2i[k] = len(self.i2c)
                    self.i2c.append(c)
                self.k2c[k] = c

    def resolve_color_name(self, color):
        if color == 'skip':
            return None
        color_tuple = ImageColor.getrgb(color)
        if len(color_tuple) == 4:
            return color_tuple
        elif len(color_tuple) == 3:
            return color_tuple + (self.alpha,)
        else:
            return None

    def get_color(self, key):
        if not key:
            return None
        return self.k2c.get(key, self.default_color)
    
    def get_name(self, key):
        if not key:
            return self.default_name
        return self.k2n.get(key, self.default_name)

class Lmap(object):
    def __init__(self, biome):
        im = Image.open(biome).convert('L')
        b = im.tobytes()
        self.bytes = struct.unpack('B'*len(b), b)
        self.w, self.h = im.size

    def get(self, x, y):
        return self.bytes[x + y * self.w]


@lru_cache(maxsize=1024)
def load_cell_biome(path, cx, cy):
    biome = os.path.join(path, 'biomemap_{}_{}.png'.format(cx, cy))
    if os.path.isfile(biome):
        return Lmap(biome)
    return None


class CellGetterB42(object):
    def __init__(self, path):
        self.path = path

    def __call__(self, cx, cy):
        return load_cell_biome(self.path, cx, cy)


def get_biome_mapping(pz_root):
    path = os.path.join(pz_root, 'media', 'lua', 'server', 'metazones')
    config_file = os.path.join(path, 'BiomeMapConfig.lua')
    if os.path.isfile(config_file):
        config = lua_util.run_and_get_var(config_file, 'biome_map_config')
        mapping = [None] * 256
        for o in config:
            mapping[o['pixel']] = o['zone']
        return mapping
    return None


def forward(x, y, remain, width):
    x += remain
    l, x = divmod(x, width)
    y += l
    return x, y

def segmentation(x, y, remain, width):
    if remain <= 0 or width <= 0:
        return []

    ops = []

    # 1) First partial row when starting in the middle of a row.
    if x != 0:
        rw = min(remain, width - x)
        ops.append((x, y, rw, 1))
        remain -= rw
        y += 1

    if remain <= 0:
        return ops

    # 2) Middle area made of whole rows.
    rows, tail = divmod(remain, width)
    if rows > 0:
        ops.append((0, y, width, rows))
        y += rows

    # 3) Last partial row.
    if tail > 0:
        ops.append((0, y, tail, 1))

    return ops

class ForagingBase(object):
    def __init__(self, **options):
        self.input = options.get('input')
        legends = options.get('foraging_color', {})
        color_default = options.get('foraging_color_default', 'Gray')
        self.color_map = ColorMapper(legends, color_default, 128)
        self.mapping = get_biome_mapping(options.get('pz_root', '.'))
        self.color_map.init(self.mapping)
        if self.mapping:
            self.version = 'B42'
            self.getter = CellGetterB42(os.path.join(self.input, 'maps'))
            self.used_types = set(self.mapping)
            self.used_types.discard(None)
        else:
            self.version = 'B41'
            objects_path = os.path.join(self.input, 'objects.lua')
            self.getter = pzobjects.CachedSquareMapGetter(
                objects_path, non_skip_key_set(legends), [0, 1])
            self.cells = self.getter.get_cell_zones().cells
            self.used_types = self.getter.get_cell_zones().used_types
            self.valid_cell = self.valid_cell_B41

        self.legends = {}
        for k, v in legends.items():
            if k in self.used_types and v != 'skip':
                self.legends[k] = v

        print('Foraging veriosn: {}'.format(self.version))

    def update_options(self, options):
        options['render_minlayer'] = 0
        options['render_maxlayer'] = 1
        options['render_margin'] = None
        options['legends'] = self.legends
        if self.version == 'B42':
            options['source_tags'] = ['foraging']
        return options

    def valid_cell_B41(self, x, y):
        return (x, y) in self.cells

    def values_fill(self, im_getter, dzi, values, width):
        draw = None
        x = 0
        y = 0
        remain = 0
        tailing_wildcards = 0
        # None: must be empty
        # False: wildcard, can be any type
        # last will never be False
        last = None
        for v in itertools.chain(values, [None]):
            if v == last:
                remain += 1
                tailing_wildcards = 0
                continue

            if v is False:
                remain += 1
                tailing_wildcards += 1
                continue

            if last is not None:
                color = self.color_map.i2c[last]
                if color is not None:
                    ops = segmentation(x, y, remain - tailing_wildcards, width)
                    if ops and draw is None:
                        draw = im_getter.get_draw()
                    for ox, oy, rw, rh in ops:
                        self.fill_rect(draw, dzi, ox, oy, rw, rh, color)

            x, y = forward(x, y, remain, width)
            remain = 1
            last = v
            tailing_wildcards = 0


class ForagingRender(ForagingBase):
    def square_B41(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        zone = self.getter(cx, cy)
        if not zone:
            return
        zone_type = zone.get((subx, suby))
        if not zone_type:
            return
        color = self.color_map.get_color(zone_type)
        if color:
            draw = im_getter.get_draw()
            draw_square(draw, ox, oy, color)

    def init_dzi(self, dzi):
        self.ox = dzi.tile_size >> 1
        self.oy = - dzi.tile_size >> 2
        self.og = dzi.grid_per_tilex >> 1
        self.values_width = (dzi.grid_per_tilex + dzi.grid_per_tiley + 2) >> 1
        if self.version == 'B42':
            self.tile = self.scan_tile
        else:
            self.square = self.square_B41

    def fill_rect(self, draw, dzi, x, y, rw, rh, color):
        dx = pzdzi.IsoDZI.GRID_WIDTH * (x - y)
        dy = pzdzi.IsoDZI.GRID_HEIGHT * (x + y)
        draw_square(draw, self.ox + dx, self.oy + dy, color, rw, rh)

    def scan_tile(self, im_getter, dzi, gx0, gy0, layer):
        x0 = (gx0 + gy0) >> 1
        y0 = (gy0 - gx0 - dzi.grid_per_tilex) >> 1
        cell = dzi.cell_size
        values = [False] * (self.values_width * self.values_width)
        cy, suby = divmod(y0 - 1, cell)
        for y in range(self.values_width):
            suby += 1
            if suby == cell:
                suby = 0
                cy += 1
            xmin = abs(y - self.og)
            xmax = min(dzi.grid_per_tilex + y - self.og, dzi.grid_per_tiley - y + self.og) + 1
            cx, subx = divmod(x0 + xmin - 1, cell)
            zone = self.getter(cx, cy)
            for x in range(xmin, xmax):
                subx += 1
                if subx == cell:
                    subx = 0
                    cx += 1
                    zone = self.getter(cx, cy)
                if zone:
                    values[x + y * self.values_width] = zone.get(subx, suby)
        self.values_fill(im_getter, dzi, values, self.values_width)


class ForagingTopRender(ForagingBase):
    def sparse_fill(self, im_getter, dzi, cx, cy, layer):
        zone = self.getter(cx, cy)
        if not zone:
            return
        draw = im_getter.get_draw()
        size = dzi.square_size
        for (x, y), t in zone.items():
            color = self.color_map.get_color(t)
            if color is not None:
                self.fill_rect(draw, dzi, x, y, 1, 1, color)

    def fill_rect(self, draw, dzi, x, y, rw, rh, color):
        size = dzi.square_size
        shape = [x * size, y * size, (x + rw) * size - 1, (y + rh) * size - 1]
        draw.rectangle(shape, fill=color)
                    
    def tile(self, im_getter, dzi, cx, cy, layer):
        if self.version == 'B41':
            return self.sparse_fill(im_getter, dzi, cx, cy, layer)
        
        zone = self.getter(cx, cy)
        if not zone:
            return
        self.values_fill(im_getter, dzi, zone.bytes, dzi.cell_size)


class ObjectsRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        legends = options.get('objects_color', {})
        color_default = options.get('objects_color_default', 'White')
        self.color_map = ColorMapper(legends, color_default, 255)
        self.color_map.init()
        font_name = options.get('objects_font')
        if not font_name:
            font_name = options.get('default_font', 'arial.tff')
        font_size = options.get('objects_font_size')
        if not font_size:
            font_size = options.get('default_font_size', 20)
        self.font = LazyFont(font_name, int(font_size))
        objects_path = os.path.join(self.input, 'objects.lua')

        types = non_skip_key_set(legends)
        self.getter = pzobjects.CachedBorderLabelMapGetter(objects_path, types)
        self.cells = self.getter.get_cell_zones().cells
        self.used_types = self.getter.get_cell_zones().used_types

        self.legends = {}
        for k, v in legends.items():
            if k in self.used_types and v != 'skip':
                self.legends[k] = v

        if options.get('use_mark'):
            self.mark = ObjectsMark(objects_path, types,
                                    self.color_map, **options)
            self.NO_IMAGE = True

    def render(self, dzi):
        return self.mark.process(dzi)

    def update_options(self, options):
        options['render_margin'] = (-2, -2, 2, 2)  # add margin for text
        options['legends'] = self.legends
        return options

    def valid_cell(self, x, y):
        return (x, y) in self.cells

    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        border, label = self.getter(cx, cy)
        if not border:
            return
        drawing = []
        if layer in border:
            if (sx, sy) in border[layer]:
                for t, flag in border[layer][sx, sy]:
                    color = self.color_map.get_color(t)
                    if color:
                        drawing.append((render_edge, (color, 3, flag)))
        if layer in label:
            if (sx, sy) in label[layer]:
                for t, name in label[layer][sx, sy]:
                    color = self.color_map.get_color(t)
                    if color:
                        drawing.append((render_long_text,
                                        (name, color, self.font.get())))
        if drawing:
            draw = im_getter.get_draw()
            for func, args in drawing:
                func(draw, ox, oy, *args)


class ObjectsMark(object):
    def __init__(self, objects_path, types, color_map, **options):
        self.objects_path = objects_path
        self.types = types
        self.output = options.get('output')
        self.encoding = options.get('encoding')
        self.map_name = options.get('cache_name', 'unknown')
        self.color_map = color_map

    def process(self, dzi):
        marks = self.get_objects_marks()
        print('  objects: {}'.format(len(marks)))
        if marks:
            output_path = os.path.join(self.output, 'marks.json')
            dump_marks(marks, output_path)
        return True

    def get_objects_marks(self):
        objects_raw = pzobjects.load_typed_objects(
            self.objects_path, types=self.types)
        objects = map(pzobjects.Obj, objects_raw)
        marks = []
        for i, obj in enumerate(objects):
            rects = [
                {'x': x, 'y': y, 'width': w, 'height': h}
                for x, y, w, h in obj.rects()
            ]
            marks.append({
                'type': 'area',
                'color': self.color_map.get_name(obj.type),
                'layer': obj.z,
                'name': obj.obj.get('name', ''),
                'rects': rects,
            })
        return marks
