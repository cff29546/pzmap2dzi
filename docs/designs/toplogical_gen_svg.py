import os
import sys
import copy

def _g(f):
    # format float
    return '{:g}'.format(f)

def _coords(c):
    return ' '.join(map(lambda x: ','.join(map(_g, x)), c))

def _style(s):
    return ';'.join(map(lambda x: ':'.join(map(str, x)), s.items()))

class Elem(object):
    def __init__(self, tag):
        self.tag = tag
        self.prop = {}

    def _prop(self):
        if hasattr(self, 'update_prop'):
            self.update_prop()
        prop = []
        for k, v in self.prop.items():
            prop.append('{}="{}"'.format(k, v))
        return ' '.join(prop)

    def __getitem__(self, key):
        return self.prop.get(key)

    def __setitem__(self, key, value):
        self.prop[key] = value

    def __delitem__(self, key):
        del self.prop[key]

    def __str__(self):
        content = self.get_content()
        if content:
            return '<{} {}>{}</{}>'.format(
                    self.tag,
                    self._prop(),
                    content,
                    self.tag)
        else:
            return '<{} {} />'.format(
                    self.tag,
                    self._prop())

class Animate(Elem):
    def __init__(self, tag_id, attr, begin, dur, v0, v1=None, discrete=False):
        super().__init__('animate')
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
        super().__init__(tag)
        self.coords = coords
        self.sizes = sizes
        self.width = width
        self.children = []
        self.style = dict(style)

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
    def __init__(self, coords, width=1, style={}):
        super().__init__('polyline', coords, [], width, style)
        if 'stroke' not in self.style:
            self.style['stroke'] = 'black'

    def update_prop(self):
        self['points'] = _coords(self.coords)
        self.update_style_prop()

class Polygon(Polyline):
    def __init__(self, coords, width=1, style={}):
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
    def __init__(self, x, y, text, fill, size):
        super().__init__('text', [[x, y]], [], size, {})
        self.children.append(text)
        self.fill = fill

    def update_prop(self):
        self['x'], self['y'] = map(_g, self.coords[0])
        self['fill'] = self.fill
        self['font-size'] = self.width


def zorder(x, y):
    block = 1
    bit = 1
    idx = 0
    m = max(x, y)
    while bit <= m:
        if bit & x:
            idx |= block
        block <<= 1
        if bit & y:
            idx |= block
        block <<= 1
        bit <<= 1
    return idx


def tangram_svg(size):
    tangram = SVG(size, size)
    tangram.append(Polygon([(0, 0), (size / 2, 0), (0, size / 2)], width=0, style={'fill': 'red'}))
    tangram.append(Polygon([(size / 2, 0), (size, 0), (size * 3 / 4, size / 4), (size / 4, size / 4)], width=0, style={'fill': 'gold'}))
    tangram.append(Polygon([(size / 2, size / 2), (size * 3 / 4, size / 4), (size / 4, size / 4)], width=0, style={'fill': 'indigo'}))
    tangram.append(Polygon([(size / 2, size / 2), (size / 4, size / 4), (0, size / 2), (size / 4, size * 3 / 4)], width=0, style={'fill': 'skyblue'}))
    tangram.append(Polygon([(0, size / 2), (size / 4, size * 3 / 4), (0, size)], width=0, style={'fill': 'plum'}))
    tangram.append(Polygon([(size / 2, size / 2), (size, size), (0, size)], width=0, style={'fill': 'orange'}))
    tangram.append(Polygon([(size / 2, size / 2), (size, size), (size, 0)], width=0, style={'fill': 'green'}))
    return tangram.move(-size / 2, -size / 2)

def rect_polygon(size, width):
    half = size / 2
    return Polygon([(-half, -half), (half, -half), (half, half), (-half, half)], width=width, style={'stroke': 'gray', 'fill': 'none'})

def add_ani(r, tag, attr, ani_list):
    ani_list = list(ani_list)
    count = len(ani_list)
    for i, (time, value) in enumerate(ani_list):
        ani_id = 'a_{}_{}'.format(tag, i)
        if i:
            begin = 'a_{}_{}.end'.format(tag, i - 1)
        else:
            begin = '0s;a_{}_{}.end'.format(tag, count - 1)
        a = Animate(ani_id, attr, begin, time, value)
        r.append(a)

def stime(z, level):
    # bottom level == 0
    
    t = 0
    # layers below
    if level:
        zl = z + 1
        for l in range(level):
            zl *= 4
            t += zl + (zl // 4)
        t -= 1
    # current layer
    t += (z + 1) + (z // 4)
    
    while z:
        z //= 4
        t += z + (z // 4)

    return t

def etime(z, level):
    return stime(z//4, level+1) + 1

def toplogical_svg(rsize, levels=3, use_image=False):

    #rsize = 50
    rect = rect_polygon(rsize, 4)

    legends = [
        ['Unprocessed'],
        ['Done, Cached'],
        ['Presisted', '(Cache Released)'],
    ]
    if use_image:
        colors = ['white', 'white', 'black']
        opacities = [1, 0, 0.75]
        use_opacity = True
        image = tangram_svg(rsize)
    else:
        colors = ['white', 'orange', 'skyblue']
        opacities = [1, 1, 1]
        use_opacity = False
        image = SVG(0, 0)

    svg = SVG(0, 0)

    # legends
    fsize = 24
    x, y = 5.5*rsize, rsize
    for text_list, color, opacity in zip(legends, colors, opacities):
        svg.paste(image, x, y)
        r = rect.copyby(x, y)
        r.style['fill'] = color
        if opacity != 1:
            r.style['fill-opacity'] = opacity
        svg.append(r)
        for i, text in enumerate(text_list):
            t = Text(x - rsize/4, y + rsize/2 + 1.5*fsize, text, 'black', str(fsize))
            svg.append(t)
            x += fsize/2
            y += fsize
        x += (rsize + 2*fsize)/2
        y += rsize + 2*fsize

    total = stime(0, levels-1) + 5

    # pyramids
    cx = rsize / 2
    cy = rsize
    for l in range(levels):
        svg.paste(image, cx, cy)
        image.matrix(2, 0, 0, 2)
        level = levels - l - 1
        if l == 0:
            coords = [0]
        else:
            tiles = 2**(l-1)
            coords = list(range(int((0.5-tiles)*rsize), tiles*rsize, rsize))
        for i, x in enumerate(coords):
            for j, y in enumerate(coords):
                z = zorder(i, j)
                s = stime(z, level)
                if l == 0:
                    e = s + 2
                else:
                    e = etime(z, level)
                r = rect.copyby(cx + x, cy + y)
                add_ani(r, f'{l}_{z}', 'fill', zip([s, e - s, total - e], colors))
                if use_opacity:
                    add_ani(r, f'o_{l}_{z}', 'fill-opacity', zip([s, e - s, total - e], opacities))
                svg.append(r)

        if l == 0:
            dy = 2 * rsize
        else:
            dy = (3 * tiles + 0.5) * rsize
        cy += dy
        cx += dy / 2

    svg.matrix(1, -0.5, 0, 0.75)

    xshift = (1.5*tiles+0.5)*rsize
    w = max(6*rsize, 4*rsize + 8*fsize, xshift)
    h = int(max(y, cy - 2*tiles*rsize)*.75)
    svg.move(xshift, 0)
    w += xshift
    svg.resize(w, h)

    box = Rect(0, 0, w, h, width=4, style={'stroke': 'gray', 'fill': 'none'})
    svg.append(box)

    return svg

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Toplogical SVG generator')
    parser.add_argument('-s', '--tile-size', type=int, default=50, help='tile size')
    parser.add_argument('-l', '--levels', type=int, default=3, help='levels')
    parser.add_argument('-i', '--use-image', action='store_true', help='use image background')
    parser.add_argument('-o', '--output', type=str, default='./toplogical.svg', help='use image background')
    args = parser.parse_args()
    toplogical_svg(args.tile_size, args.levels, args.use_image).save(args.output)



