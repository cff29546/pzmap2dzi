from PIL import Image, ImageDraw
import os
import struct
from .common import draw_square, render_long_text, render_edge, LazyFont
from .. import pzobjects

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

FORAGING_COLOR = {
    'Nav':         (0xFF, 0xFF, 0xFF, 0x80),
    'TownZone':    (   0,    0, 0xFF, 0x80),
    'TrailerPark': (   0, 0xFF, 0xFF, 0x80),
    'Vegitation':  (0xFF, 0xFF,    0, 0x80),
    'Forest':      (   0, 0xFF,    0, 0x80),
    'DeepForest':  (   0, 0x88,    0, 0x80),
    'FarmLand':    (0xFF,    0, 0xFF, 0x80),
    'Farm':        (0xFF,    0,    0, 0x80),
    'ForagingNav': (0xFF, 0xFF, 0xFF, 0x80), # B42
    'Water':       (   0, 0xBF, 0xFF, 0x80), # B42
    'WaterNoFish': (0x70, 0x80, 0x90, 0x80), # B42
}

class Lmap(object):
    def __init__(self, biome):
        im = Image.open(biome).convert('L')
        b = im.tobytes()
        self.bytes = struct.unpack('B'*len(b), b)
        self.w, self.h = im.size

    def __getitem__(self, key):
        x, y = key
        return self.bytes[x + y * self.w]


@lru_cache(maxsize=1024)
def load_cell_biome(path, cx, cy):
    biome = os.path.join(path, 'biomemap_{}_{}.png'.format(cx, cy))
    if os.path.isfile(biome):
        return Lmap(biome)
    return None


def get_biome_mapping(pz_root):
    # return None # force B41
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
        self.mapping = get_biome_mapping(options.get('pz_root', '.'))
        if self.mapping:
            self.version = 'B42'
            self.biome_path = os.path.join(self.input, 'maps')
        else:
            self.version = 'B41'
            objects_path = os.path.join(self.input, 'objects.lua')
            self.getter = pzobjects.CachedSquareMapGetter(
                objects_path, pzobjects.FORAGING_TYPES, [0, 1])
        if hasattr(self, 'tile_' + self.version):
            self.tile = getattr(self, 'tile_' + self.version)
        else:
            self.square = getattr(self, 'square_' + self.version)
        print('Foraging veriosn: {}'.format(self.version))

    def update_options(self, options):
        options['render_minlayer'] = 0
        options['render_maxlayer'] = 1
        return options


class ForagingRender(ForagingBase):
    def __init__(self, **options):
        ForagingBase.__init__(self, **options)
        if self.version == 'B41':
            self.cells = set(self.getter.get_cell_zones().keys())
            self.valid_cell = self.valid_cell_B41

    def valid_cell_B41(self, x, y):
        return (x, y) in self.cells

    def square_B41(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        zone = self.getter(cx, cy)
        if not zone:
            return
        zone_type = zone.get((sx, sy), None)
        if zone_type is None:
            return
        im = im_getter.get()
        draw = ImageDraw.Draw(im)
        color = FORAGING_COLOR[zone_type]
        draw_square(draw, ox, oy, color)

    def square_B42(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        zone = load_cell_biome(self.biome_path, cx, cy)
        if not zone:
            return
        zone_pixel = zone[subx, suby]
        zone_type = self.mapping[zone_pixel]
        if zone_type is None:
            return
        im = im_getter.get()
        draw = ImageDraw.Draw(im)
        color = FORAGING_COLOR[zone_type]
        draw_square(draw, ox, oy, color)



class ForagingTopRender(ForagingBase):
    def __init__(self, **options):
        ForagingBase.__init__(self, **options)

    def tile_B41(self, im_getter, dzi, cx, cy, layer):
        zone = self.getter(cx, cy)
        if not zone:
            return
        im = None
        draw = None
        size = dzi.square_size
        for x in range(dzi.cell_size):
            sx = x + cx*dzi.cell_size
            for y in range(dzi.cell_size):
                sy = y + cy*dzi.cell_size
                zone_type = zone.get((sx, sy), None)
                if zone_type:
                    if draw is None:
                        im = im_getter.get()
                        draw = ImageDraw.Draw(im)
                    ox = x*size
                    oy = y*size
                    shape = [ox, oy, ox + size, oy + size]
                    draw.rectangle(shape, fill=FORAGING_COLOR[zone_type])


    def tile_B42(self, im_getter, dzi, cx, cy, layer):
        zone = load_cell_biome(self.biome_path, cx, cy)
        if not zone:
            return
        im = None
        draw = None
        size = dzi.square_size
        for x in range(dzi.cell_size):
            for y in range(dzi.cell_size):
                zone_pixel = zone[x, y]
                zone_type = self.mapping[zone_pixel]
                if zone_type:
                    if draw is None:
                        im = im_getter.get()
                        draw = ImageDraw.Draw(im)
                    ox = x*size
                    oy = y*size
                    shape = [ox, oy, ox + size, oy + size]
                    draw.rectangle(shape, fill=FORAGING_COLOR[zone_type])


# objects
COLOR_MAP = {
    'ZombiesType': 'red',
    'ParkingStall': 'blue',
    'ZoneStory': 'yellow',
}
DEFAULT_COLOR = 'white'
class ObjectsRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        font_name = options.get('objects_font')
        if not font_name:
            font_name = options.get('default_font', 'arial.tff')
        font_size = options.get('objects_font_size')
        if not font_size:
            font_size = options.get('default_font_size', 20)
        self.font = LazyFont(font_name, int(font_size))
        objects_path = os.path.join(self.input, 'objects.lua')
        types = set()
        if options.get('vehicle', True):
            types = types.union(pzobjects.PARKING_TYPES)
        if options.get('special_zombie', True):
            types = types.union(pzobjects.ZOMBIE_TYPES)
        if options.get('story', True):
            types = types.union(pzobjects.STORY_TYPES)
        self.getter = pzobjects.CachedBorderLabelMapGetter(objects_path, types)
        self.cells = set(self.getter.get_cell_zones().keys())

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
                    color = COLOR_MAP.get(t, DEFAULT_COLOR)
                    drawing.append((render_edge, (color, 3, flag)))
        if layer in label:
            if (sx, sy) in label[layer]:
                for t, name in label[layer][sx, sy]:
                    color = COLOR_MAP.get(t, DEFAULT_COLOR)
                    drawing.append((render_long_text, (name, color, self.font.get())))
        if drawing:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            for func, args in drawing:
                func(draw, ox, oy, *args)

