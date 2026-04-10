"""Validation helpers for old coordinate mapping.

This script focuses on the current (old) conservative mapping in IsoDZI:
* cell -> potentially affected tiles (existing implementation)
* tile -> source squares that contribute to rendering (derived from render_tile)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, Iterable, List, Set, Tuple

from PIL import Image, ImageDraw
import random
import argparse

# Allow running this file directly: `python scripts/test_coord_mapping.py`.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pzmap2dzi.pzdzi import IsoDZI, align_origin


Square = Tuple[int, int]
Tile = Tuple[int, int]
Cell = Tuple[int, int]


def build_mock_isodzi(
    cell_size: int = 256,
    minlayer: int = -32,
    maxlayer: int = 32,
    tile_size: int = 1024,
) -> IsoDZI:
    """Create an IsoDZI-like object without reading game files.

    The returned object is initialized with the minimum fields needed by the
    coordinate mapping methods (`cell_grid_bound`, `cell2tiles`, `tile2grid`).

    use default margins
    set gxo = 0, gyo = 0
    """

    dzi = IsoDZI.__new__(IsoDZI)

    # Core map/tile config required by mapping helpers.
    dzi.cell_size = cell_size
    dzi.minlayer = minlayer
    dzi.maxlayer = maxlayer
    dzi.tile_size = tile_size

    # Derived tile-grid sizes used by tile/grid conversions.
    dzi.grid_per_tilex = dzi.tile_size // IsoDZI.GRID_WIDTH
    dzi.grid_per_tiley = dzi.tile_size // IsoDZI.GRID_HEIGHT

    # Keep margin behavior consistent with IsoDZI defaults.
    dzi.output_margin = dzi.get_output_margin()
    dzi.render_margin = dzi.get_texture_render_margin(True)
    # if render margin is a falsy value, (0, 0, 0, 0) will be used
    dzi.affected_margin = dzi.render2affected(dzi.render_margin, 'output')
    dzi.affected_margin_single_layers = dzi.render2affected(dzi.render_margin, 'single')

    # Requested fixed origin for this standalone validation script.
    dzi.gxo = 0
    dzi.gyo = 0

    return dzi


def collect_source_squares_for_tile_single_layer(
    dzi: IsoDZI, tx: int, ty: int, layer: int
) -> Set[Square]:
    """Collect all source squares that can contribute to one tile render within single layer.

    This mirrors IsoDZI.render_tile grid iteration exactly, but only records
    source square coordinates (sx, sy).
    """

    gx0, gy0 = dzi.tile2grid(tx, ty, layer)
    gx1 = gx0 + dzi.grid_per_tilex
    gy1 = gy0 + dzi.grid_per_tiley
    left, top, right, bottom = gx0, gy0, gx1, gy1

    if dzi.render_margin:
        left, top, right, bottom = map(
            sum, zip((left, top, right, bottom), dzi.render_margin)
        )

    contributors: Set[Square] = set()
    for gy in range(top, bottom + 1):
        for gx in range(left, right + 1):
            # Only even (gx + gy) map to integer source squares.
            if (gx + gy) & 1:
                continue
            sx = (gx + gy) >> 1
            sy = (gy - gx) >> 1
            contributors.add((sx, sy))
    return contributors


def collect_source_squares_for_tile(
    dzi: IsoDZI, tx: int, ty: int
) -> Set[Square]:
    """Collect all source squares that can contribute to one tile render."""
    squares = set()
    for layer in range(dzi.minlayer, dzi.maxlayer + 1):
        s = collect_source_squares_for_tile_single_layer(dzi, tx, ty, layer)
        squares.update(s)
    return squares


def squares_in_rectangle(squares: Set[Square], sx0: int, sy0: int, w: int, h: int) -> bool:
    """Return if the squares set have any square in the given rectangle."""
    for sx, sy in squares:
        if sx0 <= sx < sx0 + w and sy0 <= sy < sy0 + h:
            return True
    return False


def expand_tiles(tiles: Iterable[Tile]) -> Set[Tile]:
    """Expand the tile set by one layer of neighbours in all 8 directions."""
    base_tiles = set(tiles)
    expanded = set()
    for tx, ty in base_tiles:
        for dtx in (-1, 0, 1):
            for dty in (-1, 0, 1):
                expanded.add((tx + dtx, ty + dty))
    return expanded - base_tiles

def test_square_range(sx, sy, w, h, tile_size=1024, minlayer=-32, maxlayer=32, mode='default', visualization='always', debug=False):
    dzi, rel = relative_squares(tile_size, minlayer, maxlayer)
    if mode == 'default':
        tiles = dzi.square_rect2tiles(sx, sy, w, h)
    else:
        tiles = dzi.square_rect2tiles_rough(sx, sy, w, h)
    if debug:
        print(f"cell ({sx}, {sy}, {w}, {h}) maps to {len(tiles)} tiles.")
        print(f"output margin: {dzi.output_margin}, render margin: {dzi.render_margin}")
        print(f"Grids per tile: {dzi.grid_per_tilex}x{dzi.grid_per_tiley}")
        octagon = dzi.square_rect2oct(sx, sy, w, h)
        for gx, gy in octagon:
            print(f"Octagon corner in grid: ({gx}, {gy})")
    expanded_tiles = expand_tiles(tiles)
    tp = set()
    fp = set()
    fn = set()
    for tx, ty in tiles:
        squares = shift_squares(dzi, rel, tx, ty)
        if squares_in_rectangle(squares, sx, sy, w, h):
            tp.add((tx, ty))
        else:
            fp.add((tx, ty))
    for tx, ty in expanded_tiles:
        squares = shift_squares(dzi, rel, tx, ty)
        if squares_in_rectangle(squares, sx, sy, w, h):
            fn.add((tx, ty))
    if (visualization == 'always' or
        (visualization == 'fn' and fn) or
        (visualization == 'fp' and fp) or
        (visualization == 'nontp' and (fp or fn))):
        visualize(dzi, sx, sy, w, h, tp, fp, fn)
    return len(tp), len(fp), len(fn)

def visualize(
    dzi: IsoDZI,
    sx: int,
    sy: int,
    w: int,
    h: int,
    tp: Set[Tile],
    fp: Set[Tile],
    fn: Set[Tile],
):
    sx0 = sx
    sy0 = sy
    sx1 = sx0 + w - 1
    sy1 = sy0 + h - 1

    # Diamond corners in (gx, gy) space.
    diamond = [
        (sx0 - sy0, sx0 + sy0),
        (sx1 - sy0, sx1 + sy0),
        (sx1 - sy1, sx1 + sy1),
        (sx0 - sy1, sx0 + sy1),
    ]
    octagon = dzi.square_rect2oct(sx, sy, w, h)

    all_tiles = set(tp) | set(fp) | set(fn)
    if not all_tiles:
        print("No tiles to visualize.")
        return

    tile_boxes = {}
    for tx, ty in all_tiles:
        gx0, gy0 = dzi.tile2grid(tx, ty, 0)
        gx1 = gx0 + dzi.grid_per_tilex
        gy1 = gy0 + dzi.grid_per_tiley
        tile_boxes[(tx, ty)] = (gx0, gy0, gx1, gy1)

    xs = [p[0] for p in diamond] + [p[0] for p in octagon]
    ys = [p[1] for p in diamond] + [p[1] for p in octagon]
    for gx0, gy0, gx1, gy1 in tile_boxes.values():
        xs.extend((gx0, gx1))
        ys.extend((gy0, gy1))

    margin_px = 30
    scale_x = 2
    scale_y = scale_x // 2
    min_x = min(xs) - 2
    max_x = max(xs) + 2
    min_y = min(ys) - 2
    max_y = max(ys) + 2
    width = (max_x - min_x + 1) * scale_x + margin_px * 2
    height = (max_y - min_y + 1) * scale_y + margin_px * 2 + 80

    def to_px(gx: int, gy: int) -> Tuple[int, int]:
        px = (gx - min_x) * scale_x + margin_px
        py = (gy - min_y) * scale_y + margin_px
        return px, py

    im = Image.new("RGBA", (width, height), (250, 250, 250, 255))
    draw = ImageDraw.Draw(im, "RGBA")

    # Draw tile categories first so the cell diamond is visible on top.
    palette = {
        "tp": ((55, 160, 70, 85), (20, 100, 35, 180), tp),
        "fp": ((230, 80, 70, 95), (150, 40, 35, 180), fp),
        "fn": ((70, 120, 230, 110), (35, 70, 150, 200), fn),
    }

    for _, (fill, outline, tiles) in palette.items():
        for tx, ty in sorted(tiles):
            gx0, gy0, gx1, gy1 = tile_boxes[(tx, ty)]
            x0, y0 = to_px(gx0, gy0)
            x1, y1 = to_px(gx1, gy1)
            if x1 < x0:
                x0, x1 = x1, x0
            if y1 < y0:
                y0, y1 = y1, y0
            draw.rectangle([x0, y0, x1, y1], fill=fill, outline=outline, width=3)

    diamond_px = [to_px(gx, gy) for gx, gy in diamond]
    draw.polygon(diamond_px, fill=None, outline=(0, 0, 0, 255), width=3)
    oct_px = [to_px(gx, gy) for gx, gy in octagon]
    draw.polygon(oct_px, fill=None, outline=(120, 40, 180, 255), width=3)

    text_y = height - 65
    draw.rectangle([10, text_y - 8, width - 10, height - 10], fill=(255, 255, 255, 220), outline=(180, 180, 180, 255))
    draw.text((20, text_y), f"Rect ({sx}, {sy}, {w}, {h})", fill=(30, 30, 30, 255))
    draw.text((160, text_y), f"TP={len(tp)}", fill=(20, 100, 35, 255))
    draw.text((250, text_y), f"FP={len(fp)}", fill=(150, 40, 35, 255))
    draw.text((340, text_y), f"FN={len(fn)}", fill=(35, 70, 150, 255))
    draw.text((430, text_y), "black=cell diamond", fill=(0, 0, 0, 255))
    draw.text((590, text_y), "purple=expanded octagon", fill=(120, 40, 180, 255))

    out_dir = os.path.join(ROOT, "output", "tmp")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"coord_mapping_{sx}_{sy}_{w}_{h}.png")
    im.save(out_path)
    print(f"Visualization saved: {out_path}")


def relative_squares(tile_size=1024, minlayer=-32, maxlayer=32) -> Set[Square]:
    """Pre-build a cache of all squares that can contribute to any tile render."""
    dzi = build_mock_isodzi(minlayer=minlayer, maxlayer=maxlayer, tile_size=tile_size)
    return dzi, collect_source_squares_for_tile(dzi, 0, 0)


def shift_squares(dzi: IsoDZI, rel_squares: Set[Square], tx: int, ty: int) -> Set[Square]:
    """Shift the relative squares cache to get the contributing squares for any tile."""
    gx0, gy0 = dzi.tile2grid(tx, ty, 0)
    shifted = set()
    for sx, sy in rel_squares:
        gx = gx0 + (sx - sy)
        gy = gy0 + (sx + sy)
        new_sx = (gx + gy) >> 1
        new_sy = (gy - gx) >> 1
        shifted.add((new_sx, new_sy))
    return shifted


def range_test(args: argparse.Namespace) -> None:
    total_tp = total_fp = total_fn = 0
    case_count = 0
    pass_count = 0
    perfect_count = 0
    for x in range(8):
        for y in range(32):
            case_count += 1
            tp, fp, fn = test_square_range(x, y, args.width, args.height, args.tile_size, args.minlayer, args.maxlayer, args.mode, args.visualization, debug=args.debug)
            total_tp += tp
            total_fp += fp
            total_fn += fn
            if not fn:
                pass_count += 1
            if fn or fp:
                print(f"Test case ({x}, {y}, {args.width}, {args.height}) had TP={tp}, FP={fp}, FN={fn}")
            else:
                perfect_count += 1

    
    print(f"Total TP={total_tp}, FP={total_fp}, FN={total_fn}")
    print(f"Overall precision={total_tp / (total_tp + total_fp) if total_tp + total_fp > 0 else 1:.2%}")
    print(f"Overall recall={total_tp / (total_tp + total_fn) if total_tp + total_fn > 0 else 1:.2%}")
    print(f"Passed {pass_count} out of {case_count} cases ({pass_count / case_count:.2%})")
    print(f"Perfect matches (TP>0, FP=0, FN=0): {perfect_count} out of {case_count} cases ({perfect_count / case_count:.2%})")

def validate_square_shift() -> None:
    dzi, rel_squares = relative_squares(1024, -32, 32)
    for _ in range(10):
        tx = random.randint(-100, 100)
        ty = random.randint(-100, 100)
        shifted = shift_squares(dzi, rel_squares, tx, ty)
        direct = collect_source_squares_for_tile(dzi, tx, ty)
        assert shifted == direct, f"Mismatch for tile ({tx}, {ty})"
        print(f"Tile ({tx}, {ty}): {len(shifted)} squares, shift method matches direct collection.")


def visualize_relative_squares(tile_size=1024, minlayer=-32, maxlayer=32) -> None:
    dzi, rel_squares = relative_squares(tile_size, minlayer, maxlayer)

    gx0, gy0 = dzi.tile2grid(0, 0, 0)
    gx1 = gx0 + dzi.grid_per_tilex
    gy1 = gy0 + dzi.grid_per_tiley

    def square_diamond(sx: int, sy: int) -> List[Tuple[int, int]]:
        center_gx = sx - sy
        center_gy = sx + sy
        return [
            (center_gx, center_gy - 1),
            (center_gx + 1, center_gy),
            (center_gx, center_gy + 1),
            (center_gx - 1, center_gy),
        ]

    all_points = [(gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)]
    for sx, sy in rel_squares:
        all_points.extend(square_diamond(sx, sy))

    margin_px = 30
    scale_x = 12
    scale_y = scale_x // 2
    min_x = min(gx for gx, _ in all_points) - 2
    max_x = max(gx for gx, _ in all_points) + 2
    min_y = min(gy for _, gy in all_points) - 2
    max_y = max(gy for _, gy in all_points) + 2
    width = (max_x - min_x + 1) * scale_x + margin_px * 2
    height = (max_y - min_y + 1) * scale_y + margin_px * 2 + 80

    def to_px(gx: int, gy: int) -> Tuple[int, int]:
        px = (gx - min_x) * scale_x + margin_px
        py = (gy - min_y) * scale_y + margin_px
        return px, py

    im = Image.new("RGBA", (width, height), (248, 248, 246, 255))
    draw = ImageDraw.Draw(im, "RGBA")

    for sx, sy in sorted(rel_squares):
        diamond = [to_px(gx, gy) for gx, gy in square_diamond(sx, sy)]
        draw.polygon(
            diamond,
            fill=(80, 140, 235, 90),
            outline=(35, 75, 150, 180),
        )

    tile_rect = [to_px(gx0, gy0), to_px(gx1, gy1)]
    draw.rectangle(tile_rect, outline=(25, 25, 25, 255), width=3)

    text_y = height - 65
    draw.rectangle(
        [10, text_y - 8, width - 10, height - 10],
        fill=(255, 255, 255, 220),
        outline=(180, 180, 180, 255),
    )
    draw.text((20, text_y), f"relative squares={len(rel_squares)}", fill=(30, 30, 30, 255))
    draw.text((220, text_y), f"tile={tile_size}px", fill=(30, 30, 30, 255))
    draw.text((320, text_y), f"layers=[{minlayer}, {maxlayer}]", fill=(30, 30, 30, 255))
    draw.text((520, text_y), "blue=source squares", fill=(35, 75, 150, 255))
    draw.text((680, text_y), "black=tile border", fill=(25, 25, 25, 255))
    
    out_path = os.path.join(ROOT, "output", f"relative_squares_{tile_size}_{minlayer}_{maxlayer}.png")
    im.save(out_path)
    print(f"Relative squares visualization saved: {out_path}")


def single(args: argparse.Namespace) -> None:
    parser = argparse.ArgumentParser(description="Test coordinate mapping for a specific square.")
    parser.add_argument("x", type=int, help="Square X coordinate")
    parser.add_argument("y", type=int, help="Square Y coordinate")
    parser.add_argument("w", type=int, help="Square width")
    parser.add_argument("h", nargs='?', type=int, help="Square height", default=None)
    parser.add_argument("-t", "--tile_size", type=int, default=1024, help="Tile size")
    parser.add_argument("-m", "--minlayer", type=int, default=-32, help="Minimum layer")
    parser.add_argument("-M", "--maxlayer", type=int, default=32, help="Maximum layer")
    parser.add_argument("--mode", choices=['default', 'rough'], default='default', help="Which mapping method to test")
    parser.add_argument("-v", "--visualization", choices=['always', 'fn', 'fp', 'nontp', 'none'], default='nontp', help="When to generate visualization")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args(args)
    if args.h is None:
        args.h = args.w
    tp, fp, fn = test_square_range(args.x, args.y, args.w, args.h, args.tile_size, args.minlayer, args.maxlayer, mode=args.mode, visualization=args.visualization, debug=args.debug)
    print(f"Test case ({args.x}, {args.y}, {args.w}, {args.h}) had TP={tp}, FP={fp}, FN={fn}")


def exhaustive(args: argparse.Namespace) -> None:
    parser = argparse.ArgumentParser(description="Run multiple random tests for coordinate mapping.")
    parser.add_argument("width", type=int, nargs='?', default=256, help="Cell size")
    parser.add_argument("height", type=int, nargs='?', help="Cell height (default: same as width)", default=None)
    parser.add_argument("-n", "--num-tests", type=int, default=10, help="Number of random tests to run")
    parser.add_argument("-t", "--tile-size", type=int, default=1024, help="Tile size")
    parser.add_argument("-m", "--minlayer", type=int, default=-32, help="Minimum layer")
    parser.add_argument("-M", "--maxlayer", type=int, default=32, help="Maximum layer")
    parser.add_argument("--mode", choices=['default', 'rough'], default='default', help="Which mapping method to test")
    parser.add_argument("-v", "--visualization", choices=['always', 'fn', 'fp', 'nontp', 'none'], default='nontp', help="When to generate visualization")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args(args)
    if args.height is None:
        args.height = args.width
    range_test(args)


def scan_tile_sources(args: argparse.Namespace) -> None:
    parser = argparse.ArgumentParser(description="Scan source squares for a range of tiles.")
    parser.add_argument("tile_size", type=int, nargs='?', default=1024, help="Tile size")
    parser.add_argument("-m", "--minlayer", type=int, default=-32, help="Minimum layer")
    parser.add_argument("-M", "--maxlayer", type=int, default=32, help="Maximum layer")
    parser.add_argument("-s", "--save", action="store_true", help="Scan save data (blocks) instead of map source (cells)")
    args = parser.parse_args(args)
    dzi = build_mock_isodzi(tile_size=args.tile_size, minlayer=args.minlayer, maxlayer=args.maxlayer)
    # real game map size
    rects = [[0, 18, 45, 45], [45, 3, 13, 60], [58, 0, 20, 63]]
    units = sum([w * h for _, _, w, h in rects])
    if args.save:
        units *= dzi.cell_size * dzi.cell_size // 64  # each block has 64 cells
    print(f"Total source units to process: {units}")
    start = time.time()
    ela = time.strftime("%H:%M:%S", time.gmtime(0))
    count = 0
    tiles = {}
    for x, y, w, h in rects:
        span = 8 if args.save else dzi.cell_size
        step = dzi.cell_size // span
        x0 = x * step
        x1 = (x + w) * step
        y0 = y * step
        y1 = (y + h) * step
        for ux in range(x0, x1):
            for uy in range(y0, y1):
                sx = ux * span
                sy = uy * span
                t = dzi.square_rect2tiles(sx, sy, span, span)
                for tx, ty in t:
                    tiles.setdefault((tx, ty), []).append((ux, uy))
                count += 1
                print(f"Processing units: {count/units:.2%} {ela}", end='\r')
            elapsed = time.time() - start
            ela = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    print()
    print(f"total {len(tiles)} tiles.")
    max_len = max(len(units) for units in tiles.values())
    print(f"max source units for one tile: {max_len}")
    print(f"memory usage: {get_mem_usage()}")


def get_mem_usage() -> str:
    import psutil
    process = psutil.Process(os.getpid())
    res = process.memory_info().rss
    for unit in ['B', 'KB', 'MB', 'GB']:
        if res < 1024:
            return f"{res:.2f} {unit}"
        res /= 1024
    return f"{res:.2f} TB"


def reverse_mapping(args: argparse.Namespace) -> None:
    parser = argparse.ArgumentParser(description="Test reverse mapping from tiles to source squares.")
    parser.add_argument("tile_size", type=int, nargs='?', default=1024, help="Tile size")
    parser.add_argument("-m", "--minlayer", type=int, default=0, help="Minimum layer")
    parser.add_argument("-M", "--maxlayer", type=int, default=1, help="Maximum layer")
    args = parser.parse_args(args)
    visualize_relative_squares(args.tile_size, args.minlayer, args.maxlayer)

CMD = {
    "s": single,
    "single": single,
    "a": exhaustive,
    "all": exhaustive,
    "scan": scan_tile_sources,
    "reverse": reverse_mapping,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test coordinate mapping for IsoDZI.")
    parser.add_argument("cmd", choices=CMD.keys(), help="Test command to run")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the test command")
    args = parser.parse_args()
    CMD[args.cmd](args.args)
    # visualize_relative_squares(1024, 0, 1)
    # visualize_relative_squares(1024, 16, 17)
    # visualize_relative_squares(1024, -16, -15)
    # validate_square_shift()