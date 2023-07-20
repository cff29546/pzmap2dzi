from PIL import ImageDraw, ImageFont
import os
from .common import draw_square, render_long_text, render_edge
from .. import pzdzi, pzobjects

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
        cell_zones = pzobjects.load_cell_zones(objects_path, pzobjects.FORAGING_TYPES, 1)
        self.cells = set(cell_zones.keys())
        self.getter = pzobjects.CachedSquareMapGetter(objects_path, pzobjects.FORAGING_TYPES, 1)

    def update_options(self, options):
        options['layers'] = 1
        return options

    def valid_cell(self, x, y):
        return (x, y) in self.cells

    def square(self, im_getter, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, pzdzi.CELL_SIZE)
        cy, suby = divmod(sy, pzdzi.CELL_SIZE)
        bx, x = divmod(subx, 10)
        by, y = divmod(suby, 10)
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
        cell_zones = pzobjects.load_cell_zones(objects_path, pzobjects.FORAGING_TYPES, 1)
        self.cells = set(cell_zones.keys())
        self.getter = pzobjects.CachedSquareMapGetter(objects_path, pzobjects.FORAGING_TYPES, 1)

    def update_options(self, options):
        options['layers'] = 1
        return options

    def tile(self, im_getter, cx, cy, layer, size):
        if (cx, cy) not in self.cells:
            return
        zone = self.getter(cx, cy)
        if not zone:
            return
        im = None
        draw = None
        for x in range(300):
            sx = x + cx * 300
            for y in range(300):
                sy = y + cy * 300
                zone_type = zone.get((sx, sy), None)
                if zone_type:
                    if draw is None:
                        im = im_getter.get()
                        draw = ImageDraw.Draw(im)
                    shape = [x * size, y * size, (x + 1) * size, (y + 1) * size]
                    draw.rectangle(shape, fill=FORAGING_COLOR[zone_type])

# objects
COLOR_MAP = {
    'ZombiesType': 'red',
    'ParkingStall': 'blue',
    'ZoneStory': 'yellow',
}
DEFAULT_COLOR = 'white'
OBJ_FONT = ImageFont.truetype("arial.ttf", 20)

class ObjectsRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        objects_path = os.path.join(self.input, 'objects.lua')
        types = set()
        if not options.get('no_car_spawn', False):
            types = types.union(pzobjects.PARKING_TYPES)
        if not options.get('no_zombie', False):
            types = types.union(pzobjects.ZOMBIE_TYPES)
        if not options.get('no_story', False):
            types = types.union(pzobjects.STORY_TYPES)
        cell_zones = pzobjects.load_cell_zones(objects_path, types)
        self.cells = set(cell_zones.keys())
        self.getter = pzobjects.CachedBorderLabelMapGetter(objects_path, types)

    def valid_cell(self, x, y):
        return (x, y) in self.cells

    def square(self, im_getter, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, pzdzi.CELL_SIZE)
        cy, suby = divmod(sy, pzdzi.CELL_SIZE)
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
                    drawing.append((render_long_text, (name, color, OBJ_FONT)))
        if drawing:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            for func, args in drawing:
                func(draw, ox, oy, *args)

