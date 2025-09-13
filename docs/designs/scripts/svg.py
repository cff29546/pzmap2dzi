import copy


def _g(f):
    # format float
    return '{:g}'.format(f)


def _coords(c):
    return ' '.join(map(lambda x: ','.join(map(_g, x)), c))


def _style(s):
    return ';'.join(map(lambda x: ':'.join(map(str, x)), s.items()))


class Elem(object):
    def __init__(self, tag: str):
        self.tag = tag
        self.prop = {}
        self.children = []
        self.style = {}

    def _prop(self):
        if hasattr(self, 'update_prop'):
            self.update_prop()
        prop = []
        for k, v in self.prop.items():
            prop.append('{}="{}"'.format(k, v))
        return prop

    def __getitem__(self, key):
        return self.prop.get(key)

    def __setitem__(self, key, value):
        self.prop[key] = value

    def __delitem__(self, key):
        del self.prop[key]

    def __str__(self):
        content = self.get_content()
        tag_prop = [self.tag] + self._prop()
        if content:
            content = '{}</{}>'.format(content, self.tag)
        else:
            content = ''
            tag_prop.append('/')
        tag_prop = ' '.join(tag_prop)
        return '<{}>{}'.format(tag_prop, content)


class Animate(Elem):
    def __init__(self, tag_id, attr, begin, dur, v0, v1=None, discrete=False):
        super().__init__(tag='animate')
        self['id'] = tag_id
        self['attributeName'] = attr
        self['begin'] = begin
        self['dur'] = dur
        self['from'] = v0

        if discrete:
            self['calcMode'] = 'discrete'
        if v1 is not None:
            self['to'] = v1
        else:
            self['to'] = v0

    def get_content(self):
        return ''


class Shape(Elem):
    def __init__(self, tag, coords, sizes, width, style):
        super().__init__(tag=tag)
        self.coords = coords
        self.sizes = sizes
        self.width = width
        self.style = copy.deepcopy(style) if style else {}

    def move(self, x, y):
        return self.matrix(1, 0, 0, 1, x, y)

    def matrix(self, a, b, c, d, tx=0, ty=0):
        coords = []
        for ox, oy in self.coords:
            x = a * ox + b * oy + tx
            y = c * ox + d * oy + ty
            coords.append([x, y])
        self.coords = coords
        for child in self.children:
            if hasattr(child, 'matrix'):
                child.matrix(a, b, c, d, tx, ty)
        return self

    def copyby(self, x, y):
        s = copy.deepcopy(self)
        s.move(x, y)
        return s

    def get_content(self):
        content = []
        for child in self.children:
            content.append(str(child))
        if content:
            return '\n' + '\n'.join(content) + '\n'
        return ''

    def update_style_prop(self):
        self.style['stroke-width'] = self.width
        self['style'] = _style(self.style)

    def append(self, shape):
        self.children.append(shape)
        return self


class SVG(Shape):
    def __init__(self, w, h):
        super().__init__('svg', [], [w, h], 0, {})

    def paste(self, svg, x=0, y=0):
        self.children.extend(svg.copyby(x, y).children)
        return self

    def resize(self, w, h):
        self.sizes = [w, h]
        return self

    def update_prop(self):
        self['width'] = _g(self.sizes[0])
        self['height'] = _g(self.sizes[1])
        self['xmlns'] = 'http://www.w3.org/2000/svg'

    def save(self, file):
        with open(file, 'w') as f:
            f.write(str(self))


class Polyline(Shape):
    def __init__(self, coords, width=1, style=None):
        super().__init__('polyline', coords, [], width, style)
        if 'stroke' not in self.style:
            self.style['stroke'] = 'black'

    def update_prop(self):
        self['points'] = _coords(self.coords)
        self.update_style_prop()


class Polygon(Polyline):
    def __init__(self, coords, width=1, style=None):
        super().__init__(coords, width, style)
        self.tag = 'polygon'


class Rect(Shape):
    def __init__(self, x, y, w, h, rx=0, ry=0, width=1, style={}):
        super().__init__('rect', [[x, y]], [w, h, rx, ry], width, style)

    def update_prop(self):
        self['x'], self['y'] = map(_g, self.coords[0])
        self['width'] = _g(self.sizes[0])
        self['height'] = _g(self.sizes[1])
        self['rx'] = _g(self.sizes[2])
        self['ry'] = _g(self.sizes[3])
        self.update_style_prop()


class Text(Shape):
    def __init__(self, x, y, text, size, style=None):
        super().__init__('text', [[x, y]], [], size, style)
        self.children.append(text)

    def update_prop(self):
        self.update_style_prop()
        self['x'], self['y'] = map(_g, self.coords[0])
        self['font-size'] = self.width


class Line(Shape):
    def __init__(self, x1, y1, x2, y2, width=1, style=None):
        super().__init__('line', [[x1, y1], [x2, y2]], [], width, style)
        if 'stroke' not in self.style:
            self.style['stroke'] = 'black'

    def update_prop(self):
        self['x1'], self['y1'] = map(_g, self.coords[0])
        self['x2'], self['y2'] = map(_g, self.coords[1])
        self.update_style_prop()
