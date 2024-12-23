from PIL import ImageDraw
import os
from .common import draw_square, render_long_text, render_edge, LazyFont
from .. import pzobjects

FORAGING_COLOR = {
    'Nav':         (255, 255, 255, 128),
    'TownZone':    (  0,   0, 255, 128),
    'TrailerPark': (  0, 255, 255, 128),
    'Vegitation':  (255, 255,   0, 128),
    'Forest':      (  0, 255,   0, 128),
    'DeepForest':  (  0, 128,   0, 128),
    'FarmLand':    (255,   0, 255, 128),
    'Farm':        (255,   0,   0, 128),
}

class ForagingRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        objects_path = os.path.join(self.input, 'objects.lua')
        self.getter = pzobjects.CachedSquareMapGetter(objects_path, pzobjects.FORAGING_TYPES, 1)
        self.cells = set(self.getter.get_cell_zones().keys())

    def update_options(self, options):
        options['render_layers'] = [0]
        return options

    def valid_cell(self, x, y):
        return (x, y) in self.cells

    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
        bx, x = divmod(subx, dzi.block_size)
        by, y = divmod(suby, dzi.block_size)
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

class ForagingTopRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        objects_path = os.path.join(self.input, 'objects.lua')
        self.getter = pzobjects.CachedSquareMapGetter(objects_path, pzobjects.FORAGING_TYPES, 1)

    def update_options(self, options):
        options['render_layers'] = [0]
        return options

    def tile(self, im_getter, dzi, cx, cy, layer):
        zone = self.getter(cx, cy)
        if not zone:
            return
        im = None
        draw = None
        for x in range(dzi.cell_size):
            sx = x + cx*dzi.cell_size
            for y in range(dzi.cell_size):
                sy = y + cy*dzi.cell_size
                zone_type = zone.get((sx, sy), None)
                if zone_type:
                    if draw is None:
                        im = im_getter.get()
                        draw = ImageDraw.Draw(im)
                    ox = x*dzi.square_size
                    oy = y*dzi.square_size
                    shape = [ox, oy, ox + dzi.square_size, oy + dzi.square_size]
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

