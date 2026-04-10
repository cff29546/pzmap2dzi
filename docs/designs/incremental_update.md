# Motivation

When the game map is updated partially or save game content changes by playing, we want to avoid re-rendering the entire map. Instead, we want to only re-render the changed tiles and new tiles.

# Design

## Goals

* Support incremental updates for both map and save renders.
* Minimal overhead for detecting changes and planning updates.
* Robust to all scenarios: partial and full source changes, partial source removal, render interruptions, and their combinations.
* For existing tiles in output from previous render runs:
    * Keep all tiles unaffected by source changes intact to minimize render time.
    * Ensure rerender of all affected tiles, including all affected thumbnail tiles in the pyramid.
* Future compatibility for states storage needed.

## Assumptions

* Assumption A: No source changes during an active render run. But changes can happen between runs (including interrupted run).
* Assumption B: Any source file updated has a newer mtime than last render time except for deleted files which are simply removed.
* Assumption C: No manual edits to output tiles. i.e. mtime of existing tiles is a reliable indicator of last render time for that tile.

## Key Idea

Treat incremental update as a selective invalidation problem:

1. Build a source snapshot for the current render input (cells for base/mod maps, blocks for save games).
2. Based on the current snapshot, previous snapshot and the mtime of existing tiles, compute the set of stale tiles that must be rerendered.
3. Propagate stale tiles to their ancestor closure in the pyramid to ensure all affected thumbnails are included.
4. Invalidate stale tiles from the output folder when scanning completed tiles.

## States/Snapshot Storage

Use JSON snapshot files under each output folder:
* `sources_current.json`: temp snapshot captured at planning stage for the current run.
* `sources.json`: last successful snapshot.

Snapshot lifecycle:
1. Build source snapshot at planning stage and write `sources_current.json`.
2. Run task planning/rendering.
3. On successful completion, move/replace `sources_current.json` to `sources.json`.

### Snapshot schema

Store a list of entries, each of format:
```json
[[x, y], [mtime, signature]]
```

## Stale Source Detection

1. Diff sources from previous snapshot to current snapshot to detect removed sources.
2. Compare the last render time of a existing tile (mtime) with the mtime of all source files that contribute to that tile. To detect stale tiles.
3. For legacy renders without snapshot, assume no deletions.

## Source Unit to Tile Mapping

### Top View Tiles

This is a straightforward mapping, as bottom-level tile coordinates (tx, ty) is an offset of cell coordinates (cx, cy).

### Isometric View Tiles

Use `dzi.square_rect2tiles()` for detecting all tiles affected by a source unit, with a worst-case margin based on the maximum layer count and tile size.

## Overwrite Guard

Before overwriting `map_info.json`, compare key geometry fields (`w`, `h`, `skip`, `x0`, `y0`, `sqr`, layer/cell/block metadata when present).
If mismatch is detected, warn and stop rendering.
This avoids unintentionally mixing outputs from different sources.
