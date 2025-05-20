# Engine Concepts (WIP)

## The Isometric Coordination System

### Squares
Squares represent the basic building blocks of the game map. Each square corresponds to a specific location where gameplay actions can take place. Visual elements such as walls, floors, and objects are assigned to these squares, allowing for detailed placement and interaction within the environment.

In the isometric coordination system, each square appears as a rhombus with its longer diagonal running horizontally. The long diagonal is precisely twice the length of the short diagonal. Moving along the `x` axis shifts position to the right and downward, while moving along the `y` axis shifts position to the left and downward.

### Cells
A cell groups together a fixed number of squares and is stored as a single map file. In game version B41 and earlier, each cell consists of `300x300` squares. Starting with version B42, the cell size is updated to `256x256` squares. This structure helps organize and manage map data efficiently.

### Blocks
A block (also referred to as a `chunk` in the game code) is a small grouping of squares used for saving game state. Each block is stored as a separate file within the savegame data. In versions up to B41, a block contains `10x10` squares. Beginning with version B42, the block size changes to `8x8` squares.

### Grids
Grids define a coordinate system that covers both the centers and corners of all squares in the map. The grid coordinate `(x=0, y=0)` is positioned at the center of the square at `(x=0, y=0)`. This system provides a precise reference for aligning and placing map elements relative to the underlying squares.

### Tiles
Tiles are the individual image segments produced for each level of the DZI pyramid. By default, each tile measures `1024x1024` pixels. The tile coordinate system starts at `(x=0, y=0)` in the top-left corner; increasing `x` moves to the right, while increasing `y` moves downward. The valid tile coordinates span the rectangular bounds of the output image. Tiles are positioned so that the grid coordinate `(x=0, y=0)` always aligns with a tile corner. The tile size must be an integer multiple of the grid size in both the x and y directions.

[coordinate example of a 16x8 square map](./img/coords.svg)

## Render Interface

### Overview
The render interface in the `pzmap2dzi` project defines how map data is transformed into image tiles for the DZI pyramid. It standardizes the process of rendering both the main game map and overlay maps, allowing them to use the same rendering logic and infrastructure. The interface provides methods to render individual squares or entire tiles, supporting efficient task scheduling and pyramid construction.

Renderers are registered in `pzmap2dzi/render.py` and their implementations are located in the `pzmap2dzi/render_impl/` directory.

### Key Methods of the Render Object

The Render object defines the core interface for converting map data into image tiles. Its main methods are:

- **Initialization**
  
  ```python
  __init__(self, **options)
  ```
  - Accepts an `options` dictionary, a duplication of `render_conf` in `conf.yaml` and updated per rendering task. See the `render_map` function in [main.py](/main.py) for usage details.

- **Rendering a Square**
  
  ```python
  square(self, im_getter, dzi, ox, oy, sx, sy, layer)
  ```
  - Renders a single square at the specified coordinates.
    - `im_getter`: Provides a lazily-initialized `Image` object for drawing.
    - `dzi`: The `DZI` configuration object (includes tile size, square size, grid range, etc.).
    - `ox`, `oy`: Pixel offsets from the tile image's top-left corner to the square center.
    - `sx`, `sy`: Square coordinates in the game world.
    - `layer`: Floor index (`0` for ground, negative for basement).

- **Rendering a Tile**
  
  ```python
  tile(self, im_getter, dzi, gx0, gy0, layer)
  ```
  - Renders an entire tile at the given grid coordinates. If implemented, this method is preferred over `square` for tile rendering.
    - `im_getter`, `dzi`, `layer`: Same as in `square`.
    - `gx0`, `gy0`: Grid coordinates of the tile image's top-left corner.

- **Updating Task-Specific Options**
  
  ```python
  update_options(self, options) -> new_options
  ```
  - Optionally updates and returns a modified options dictionary for the current rendering task. Called after the Render object is created and before passing options to the `DZI` constructor.
