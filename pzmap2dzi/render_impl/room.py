from PIL import ImageDraw
import os
from .common import render_long_text, render_edge, LazyFont
from .. import lotheader, pzdzi, geometry

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

class CellRoom(object):
    def __init__(self, rooms):
        self.name = []
        self.edge = {}
        self.label = {}
        for i, r in enumerate(rooms):
            layer = r['layer']
            self.name.append(r['name'])
            edge = geometry.rects_border(r['rects'])
            lx, ly = geometry.label_square(r['rects'])
            self.label[layer, lx, ly] = r['name']

            for (x, y), flag in edge:
                self.edge[layer, x, y] = (i, flag)

@lru_cache(maxsize=128)
def load_cell_room(path, cx, cy):
    name = os.path.join(path, '{}_{}.lotheader'.format(cx, cy))
    if not os.path.isfile(name):
        return None
    header = lotheader.load_lotheader(name)
    if len(header['rooms']) == 0:
        return None
    return CellRoom(header['rooms'])

COLOR_MAP = {
    # DumbBell/BarBell
    'gym': 'lime',

    # Sledgehammer
    'garagestorage': 'orange',   # 60 crate 100 locker 20 shelves,counter
    'storage': 'orange',
    'garage': 'orange',
    'warehouse': 'orange',
    'closet': 'orange',
    'construction': 'orange',
    'factory': 'orange',
    'firestorage': 'orange',
    'shed': 'orange',

    'pawnshop': 'orange',        # 100 crate 10 other
    'pawnshopstorage': 'orange',

    'toolstore': 'magenta',      # 100 shelves 20 other
    'storageunit': 'magenta',    # 60
    'farmstorage': 'magenta',    # 40
    'loggingfactory': 'magenta', # 20 crate 100 shelves
    'toolstorage': 'blue',       # 20
    #'kitchen': 'blue',           # 10, only in crate

    # empty
    'empty': 'silver',
    'emptyoutside': 'silver',
}
DEFAULT_COLOR = 'cyan'

class RoomRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.encoding = options.get('encoding')
        font_name = options.get('room_font')
        if not font_name:
            font_name = options.get('default_font', 'arial.tff')
        font_size = options.get('room_font_size')
        if not font_size:
            font_size = options.get('default_font_size', 20)
        self.font = LazyFont(font_name, int(font_size))

    def square(self, im_getter, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, pzdzi.CELL_SIZE)
        cy, suby = divmod(sy, pzdzi.CELL_SIZE)
        room = load_cell_room(self.input, cx, cy)
        if not room:
            return
        drawing = []
        if (layer, subx, suby) in room.label:
            raw_name = room.label[layer, subx, suby]
            name = raw_name.decode(self.encoding, errors='ignore')
            color = COLOR_MAP.get(name, DEFAULT_COLOR)
            drawing.append((render_long_text, (name, color, self.font.get())))
        if (layer, subx, suby) in room.edge:
            idx, flag = room.edge[layer, subx, suby]
            raw_name = room.name[idx]    
            name = raw_name.decode(self.encoding, errors='ignore')
            color = COLOR_MAP.get(name, DEFAULT_COLOR)
            drawing.append((render_edge, (color, 3, flag)))
        if drawing:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            for func, args in drawing:
                func(draw, ox, oy, *args)

