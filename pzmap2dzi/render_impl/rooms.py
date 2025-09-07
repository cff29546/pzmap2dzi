import os
from PIL import ImageDraw
from .common import render_long_text, render_edge, LazyFont, dump_marks
from .. import lotheader, geometry

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
    header = lotheader.load_lotheader(path, cx, cy)
    if not header:
        return None
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
        if options.get('use_mark'):
            self.mark = RoomMark(**options)
            self.NO_IMAGE = True

    def render(self, dzi):
        return self.mark.process(dzi)

    def update_options(self, options):
        options['render_margin'] = [-2, -2, 2, 2]  # add margin for text
        return options

    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        cx, subx = divmod(sx, dzi.cell_size)
        cy, suby = divmod(sy, dzi.cell_size)
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


def get_room_marks_by_cell(path, cx, cy, cell_size, encoding, map_name):
    header = lotheader.load_lotheader(path, cx, cy)
    if not header:
        return []
    dx = cx * cell_size
    dy = cy * cell_size
    marks = []
    for i, room in enumerate(header['rooms']):
        name = room['name'].decode(encoding, errors='ignore')
        layer = room['layer']
        rects = []
        for x, y, w, h in room['rects']:
            rects.append({'x': x + dx, 'y': y + dy, 'width': w, 'height': h})
        marks.append({
            'type': 'area',
            'color': COLOR_MAP.get(name, DEFAULT_COLOR),
            'name': name,
            'layer': layer,
            'rects': rects,
            #'text_position': 'top',
            #'background': 'transparent',
            #'passthrough': True,
            #'id': 'room_{}_{}_{}_{}'.format(map_name, cx, cy, i),
        })
    return marks


class RoomMark(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.output = options.get('output')
        self.encoding = options.get('encoding')
        self.map_name = options.get('cache_name', 'unknown')

    def process(self, dzi):
        marks = []
        for cx, cy in dzi.cells:
            cell_marks = get_room_marks_by_cell(self.input, cx, cy, dzi.cell_size, self.encoding, self.map_name)
            if cell_marks:
                marks.extend(cell_marks)
        print('  rooms: {}'.format(len(marks)))
        if marks:
            output_path = os.path.join(self.output, 'marks.json')
            dump_marks(marks, output_path)
        return True