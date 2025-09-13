from svg import SVG, Polygon, Shape, Text, Animate


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
    tangram.append(Polygon([(0, 0), (size / 2, 0), (0, size / 2)],
                           width=0, style={'fill': 'red'}))
    tangram.append(Polygon([(size / 2, 0), (size, 0), (size * 3 / 4, size / 4),
                            (size / 4, size / 4)],
                           width=0, style={'fill': 'gold'}))
    tangram.append(Polygon([(size / 2, size / 2), (size * 3 / 4, size / 4),
                            (size / 4, size / 4)],
                           width=0, style={'fill': 'indigo'}))
    tangram.append(Polygon([(size / 2, size / 2), (size / 4, size / 4),
                            (0, size / 2), (size / 4, size * 3 / 4)],
                           width=0, style={'fill': 'skyblue'}))
    tangram.append(Polygon([(0, size / 2), (size / 4, size * 3 / 4),
                            (0, size)], width=0, style={'fill': 'plum'}))
    tangram.append(Polygon([(size / 2, size / 2), (size, size), (0, size)],
                           width=0, style={'fill': 'orange'}))
    tangram.append(Polygon([(size / 2, size / 2), (size, size), (size, 0)],
                           width=0, style={'fill': 'green'}))
    return tangram.move(-size / 2, -size / 2)


def rect_polygon(size, width):
    half = size / 2
    return Polygon([(-half, -half), (half, -half),
                    (half, half), (-half, half)],
                   width=width, style={'stroke': 'gray', 'fill': 'none'})


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
        for i in range(level):
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

    # rsize = 50
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
    background = Shape('rect', [], [], 0, {})
    background['width'] = '100%'
    background['height'] = '100%'
    background['fill'] = 'white'
    svg.append(background)

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
            t = Text(x - rsize/4, y + rsize/2 + 1.5*fsize,
                     text, str(fsize), {'fill': 'black'})
            svg.append(t)
            x += fsize/2
            y += fsize
        x += (rsize + 2*fsize)/2
        y += rsize + 2*fsize

    total = stime(0, levels-1) + 5

    # pyramids
    cx = rsize / 2
    cy = rsize
    for lv in range(levels):
        svg.paste(image, cx, cy)
        image.matrix(2, 0, 0, 2)
        level = levels - lv - 1
        if lv == 0:
            coords = [0]
        else:
            tiles = 2**(lv-1)
            coords = list(range(int((0.5-tiles)*rsize), tiles*rsize, rsize))
        for i, x in enumerate(coords):
            for j, y in enumerate(coords):
                z = zorder(i, j)
                s = stime(z, level)
                if lv == 0:
                    e = s + 2
                else:
                    e = etime(z, level)
                r = rect.copyby(cx + x, cy + y)
                add_ani(r, f'{lv}_{z}', 'fill',
                        zip([s, e - s, total - e], colors))
                if use_opacity:
                    add_ani(r, f'o_{lv}_{z}', 'fill-opacity',
                            zip([s, e - s, total - e], opacities))
                svg.append(r)

        if lv == 0:
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
    svg['style'] = 'background-color: white;'

    # box = Rect(0, 0, w, h, width=4, style={'stroke': 'gray', 'fill': 'none'})
    # svg.append(box)

    return svg


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Toplogical SVG generator')
    parser.add_argument('-s', '--tile-size', type=int,
                        default=50, help='tile size')
    parser.add_argument('-l', '--levels', type=int,
                        default=3, help='levels')
    parser.add_argument('-i', '--use-image', action='store_true',
                        help='use image background')
    parser.add_argument('-o', '--output', type=str,
                        default='./toplogical.svg', help='output file')
    args = parser.parse_args()
    toplogical_svg(args.tile_size, args.levels,
                   args.use_image).save(args.output)
