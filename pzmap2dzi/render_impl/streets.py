import os
from xml.etree import ElementTree
from .common import dump_marks
from PIL import ImageColor


class StreetsRender(object):
    def __init__(self, **options):
        self.input = options.get('input')
        self.streets_path = os.path.join(self.input, 'streets.xml')
        c0 = options.get('streets_large', 'Orange')
        c1 = options.get('streets_medium', 'Coral')
        c2 = options.get('streets_small', 'Cyan')
        self.colors = [c0, c1, c2]
        self.colors_alpha = []
        for c in self.colors:
            rgb = ImageColor.getcolor(c, 'RGB')
            alpha_color = 'rgba({},{},{},0.5)'.format(*rgb)
            self.colors_alpha.append(alpha_color)
        self.output = options.get('output')
        self.NO_IMAGE = True

    def render(self, dzi):
        if not os.path.isfile(self.streets_path):
            return
        tree = ElementTree.parse(self.streets_path)
        root = tree.getroot()
        marks = []
        count = [0, 0, 0]
        for street in root:
            name = street.attrib.get('name', '')
            width = int(street.attrib.get('width', 0))
            for points in street:
                p = []
                for point in points:
                    x = float(point.attrib.get('x', 0))
                    y = float(point.attrib.get('y', 0))
                    p.append({'x': x, 'y': y})
                mark = { 'type': 'polyline', 'name': name, 'width': width, 'points': p }
                mark['visible_zoom_level'] = self.get_level(mark)
                mark['color'] = self.colors_alpha[mark['visible_zoom_level']]
                mark['text_color'] = self.colors[mark['visible_zoom_level']]
                marks.append(mark)
                count[mark['visible_zoom_level']] += 1
        print('  streets: {} (large {}, medium {}, small {})'.format(len(marks), count[0], count[1], count[2]))
        if marks:
            output_path = os.path.join(self.output, 'marks.json')
            dump_marks(marks, output_path)
        return True

    def get_level(self, mark):
        span = self.max_span(mark)
        width = mark.get('width', 1)
        if span > 512 or width > 12:
            return 0
        elif span > 256 or width > 8:
            return 1
        return 2

    def max_span(self, mark):
        points = mark.get('points', [])
        if not points:
            return 0
        min_x = min(p['x'] for p in points)
        max_x = max(p['x'] for p in points)
        min_y = min(p['y'] for p in points)
        max_y = max(p['y'] for p in points)
        span_x = max_x - min_x
        span_y = max_y - min_y
        return max(span_x, span_y)