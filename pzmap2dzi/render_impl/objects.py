from PIL import Image, ImageDraw, ImageColor
import os
import struct
from .common import draw_square, render_long_text, render_edge, LazyFont, dump_marks
from .. import pzobjects, geometry

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache


def non_skip_key_set(d):
    kvs = filter(lambda kv: kv[1] != 'skip', d.items())
    return set(map(lambda kv: kv[0], kvs))


class ColorMapper(object):
    def __init__(self, color_map, default_color, default_alpha=255):
        self.color_map = color_map
        self.alpha = default_alpha
        self.default = default_color
        self.cache = {}

    def apply_alpha(self, color):
        if color == 'skip':
            return None
        color_tuple = ImageColor.getrgb(color)
        if len(color_tuple) == 4:
            return color_tuple
        elif len(color_tuple) == 3:
            return color_tuple + (self.alpha,)
        else:
            return None

    def get(self, key):
        if not key:
            return None
        if key not in self.cache:
            name = self.get_name(key)
            self.cache[key] = self.apply_alpha(name)
        return self.cache[key]

    def get_name(self, key):
        if not key:
            return None
        return self.color_map.get(key, self.default)

class Lmap(object):
    def __init__(self, biome):
        im = Image.open(biome).convert('L')
        b = im.tobytes()
        self.bytes = struct.unpack('B'*len(b), b)
        self.w, self.h = im.size

    def get(self, key):
        x, y = key
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
        config = pzobjects.load_lua_raw(config_file)
        mapping = [None] * 256
        for o in config['biome_map_config']:
            mapping[o['pixel']] = o['zone']
        return mapping
    return None


class ForagingBase(object):
    def __init__(self, **options):
        self.input = options.get('input')
        legends = options.get('foraging_color', {})
        color_default = options.get('foraging_color_default', 'Gray')
        self.color_map = ColorMapper(legends, color_default, 128)
        self.mapping = get_biome_mapping(options.get('pz_root', '.'))
        if self.mapping:
            self.version = 'B42'
            self.getter = CellGetterB42(os.path.join(self.input, 'maps'))
            self.used_types = set(filter(lambda x: x is not None, self.mapping))
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
        return options

    def valid_cell_B41(self, x, y):
        return (x, y) in self.cells


class ForagingRender(ForagingBase):
    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        zone = self.getter(cx, cy)
        if not zone:
            return
        zone_type = zone.get((subx, suby))
        if self.mapping:
            zone_type = self.mapping[zone_type]
        color = self.color_map.get(zone_type)
        if color:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            draw_square(draw, ox, oy, color)


class ForagingTopRender(ForagingBase):
    def tile(self, im_getter, dzi, cx, cy, layer):
        zone = self.getter(cx, cy)
        if not zone:
            return
        im = None
        draw = None
        size = dzi.square_size
        for x in range(dzi.cell_size):
            for y in range(dzi.cell_size):
                zone_type = zone.get((x, y))
                if self.mapping:
                    zone_type = self.mapping[zone_type]
                color = self.color_map.get(zone_type)
                if color:
                    if draw is None:
                        im = im_getter.get()
                        draw = ImageDraw.Draw(im)
                    ox = x*size
                    oy = y*size
                    shape = [ox, oy, ox + size - 1, oy + size - 1]
                    draw.rectangle(shape, fill=color)


class ObjectsRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        legends = options.get('objects_color', {})
        color_default = options.get('objects_color_default', 'White')
        self.color_map = ColorMapper(legends, color_default, 255)
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
            self.mark = ObjectsMark(objects_path, types, self.color_map, **options)
            self.NO_IMAGE = True

    def render(self, dzi):
        return self.mark.process(dzi)

    def update_options(self, options):
        options['render_margin'] = [-2, -2, 2, 2]  # add margin for text
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
                    color = self.color_map.get(t)
                    if color:
                        drawing.append((render_edge, (color, 3, flag)))
        if layer in label:
            if (sx, sy) in label[layer]:
                for t, name in label[layer][sx, sy]:
                    color = self.color_map.get(t)
                    if color:
                        drawing.append((render_long_text, (name, color, self.font.get())))
        if drawing:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
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
        if marks:
            output_path = os.path.join(self.output, 'marks.json')
            dump_marks(marks, output_path)
        return True

    def get_objects_marks(self):
        objects_raw = pzobjects.load_typed_objects(self.objects_path, types=self.types)
        objects = map(pzobjects.Obj, objects_raw)
        marks = []
        for i, obj in enumerate(objects):
            rects = [{'x': x, 'y': y, 'width': w, 'height': h} for x, y, w, h in obj.rects()]
            marks.append({
                'type': 'area',
                'color': self.color_map.get_name(obj.type),
                'layer': obj.z,
                'name': obj.obj.get('name', ''),
                'rects': rects,
                #'text_position': 'top',
                #'background': 'transparent',
                #'passthrough': True,
                #'id': 'obj_{}_{}'.format(self.map_name, i),
                #'visiable_zoom_level': 2,
            })
        return marks
