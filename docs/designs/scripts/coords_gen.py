import os
import sys

from svg import SVG, Polygon, Shape, Text, Animate, Line

def coords_svg(size, num_squares_x=8, num_squares_y=8, tile_size=4):

    squares = SVG(0, 0)
    for i in range(num_squares_x + 1):
        squares.append(Line(
            i * size - size // 2, -size // 2,
            i * size - size // 2, num_squares_y * size - size // 2,
            width=1, style={'stroke': 'rgba(0, 128, 0, 0.25)'}
        ))
    for j in range(num_squares_y + 1):
        squares.append(Line(
            -size // 2, j * size - size // 2,
            num_squares_x * size - size // 2, j * size - size // 2,
            width=1, style={'stroke': 'rgba(0, 128, 0, 0.25)'}
        ))
    for i in range(num_squares_x):
        for j in range(num_squares_y):
            t = Text(
                i * size - size // 4, j * size - size // 4,
                f'Square({i},{j})', size=size // 16, style={'fill': 'green'}
            )
            t['text-anchor'] = 'middle'
            t['dominant-baseline'] = 'middle'
            squares.append(t)
    squares.matrix(0.5, -0.5, 0.25, 0.25)

    tiles = SVG(0, 0)
    tsize = size * tile_size // 2
    xmin = -num_squares_y // tile_size
    xmax = num_squares_x // tile_size - 1 if num_squares_x % tile_size == 0 else num_squares_x // tile_size
    ymin = -1
    dy = (num_squares_x + num_squares_y - 1) // 2
    ymax = dy // tile_size - 1 if dy % tile_size == 0 else dy // tile_size
    for i in range(xmin, xmax + 2):
        tiles.append(Line(
            i * tsize, ymin * tsize,
            i * tsize, (ymax + 1) * tsize,
            width=1, style={'stroke': 'red'}
        ))
    for j in range(ymin, ymax + 2):
        tiles.append(Line(
            xmin * tsize, j * tsize,
            (xmax + 1) * tsize, j * tsize,
            width=1, style={'stroke': 'red'}
        ))
    for i in range(xmin, xmax + 1):
        for j in range(ymin, ymax + 1):
            t = Text(
                i * tsize, j * tsize,
                f'Tile({i-xmin},{j-ymin})', size=size // 16, style={'fill': 'red'}
            )
            t['text-anchor'] = 'left'
            t['dominant-baseline'] = 'hanging'
            tiles.append(t)

    grids = SVG(0, 0)
    gxmin = xmin * tile_size
    gxmax = (xmax + 1) * tile_size + 1
    gymin = ymin * tile_size * 2
    gymax = (ymax + 1) * tile_size * 2 + 1
    for i in range(gxmin, gxmax + 1):
        grids.append(Line(
            i * size // 2, gymin * size // 4,
            i * size // 2, gymax * size // 4,
            width=1, style={'stroke': 'rgba(128, 0, 128, 0.1)'}
        ))
    for j in range(gymin, gymax + 1):
        grids.append(Line(
            gxmin * size // 2, j * size // 4,
            gxmax * size // 2, j * size // 4,
            width=1, style={'stroke': 'rgba(128, 0, 128, 0.1)'}
        ))
    for i in range(gxmin, gxmax):
        for j in range(gymin, gymax):
            t = Text(
                i * size // 2, j * size // 4,
                f'Grid({i},{j})', size=size // 16, style={'fill': 'purple'}
            )
            t['text-anchor'] = 'middle'
            t['dominant-baseline'] = 'middle'
            grids.append(t)

    w = tsize * (xmax - xmin + 1)
    h = tsize * (ymax - ymin + 1)
    ox = -xmin * tsize
    oy = tsize
    svg = SVG(w, h)
    svg.paste(squares, ox, oy)
    svg.paste(grids, ox, oy)
    svg.paste(tiles, ox, oy)
    svg['style'] = 'background-color: white;'
    return svg

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Coords SVG generator')
    parser.add_argument('-s', '--square-size', type=int, default=64, help='square size')
    parser.add_argument('-x', '--num-squares-x', type=int, default=8, help='number of squares in x direction')
    parser.add_argument('-y', '--num-squares-y', type=int, default=8, help='number of squares in y direction')
    parser.add_argument('-t', '--tile-size', type=int, default=4, help='tile size')
    parser.add_argument('-o', '--output', type=str, default='./coords.svg', help='output file')
    args = parser.parse_args()
    coords_svg(args.square_size, args.num_squares_x, args.num_squares_y, args.tile_size).save(args.output)



