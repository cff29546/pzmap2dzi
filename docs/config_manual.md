# Configurations Variables
  - How to find configurations variables \
    Configurations variables are located in the config.txt file in the root folder.

  - Basic Options
     - **python** \
       This variable allows change of the Python executable used \
       For example: set `python=py -3` force the use of python 3.x
     - **pz_path** \
       This variable should be set to the path of your ProjectZomboid game folder. \
       For example: `pz_path=D:\SteamLibrary\steamapps\common\ProjectZomboid`
     - **out_path** \
       This variable should be set to desired output location. \
       For example: `out_path=E:\pzmap`
     - **map_path** \
       This variable should be set to the path of a map you want to render. \
       For example: `map_path=D:\SteamLibrary\steamapps\common\ProjectZomboid\media\maps\Muldraugh, KY`
     - **additional_texture_packs** \
       This variable should include additional texture packs needed for a modded map, use space to separate multiple texture packs \
       For example: `additional_texture_packs=D:\SteamLibrary\steamapps\workshop\content\108600\2888082232\mods\CamdenCounty\media\texturepacks\MyTiles.pack`

  - Common Render Options (**common_param=**) \
    Common Render Options affect all render tasks
    - **-m <threads count>** \
      How many threads (workers) do you want to use for rendering \
      For example: set `-m 16` to use 16 threads
    - **-v** \
      Verbose. If present, additional information about rendering progress will be printed on the console.
    - **-s <stop key>** \
      Set a hotkey to stop rendering. Render progress stopped in this way can be resumed later \
      For example: set `-s "<f9>"` use F9 as the stop key
    - **--profile** \
      If present, additional profiling information will be printed

  - Top View Render Options (**common_top_param**) \
    Top View Render Options affect all top view render tasks
    - **--square-size <pixels>** \
      Size in pixels of a square in the top view map \
      For example, set `--square-size 10` uses a 10x10 square for each in-game floor square

  - Task Related Options \
    Each render task has its option variable:
    - **base_param**: main isometric map
    - **base_top_param**: main top view map
    - **grid_param**: isometric grid
    - **grid_top_param**: top view grid
    - **foraging_param**: isometric foraging map
    - **foraging_top_param**: top view foraging map
    - **objects_param**: isometric objects map (story, parking, special zombie areas)
    - **room_param**: isometric room info map
    - **zombie_param**: isometric zombie heatmap
    - **zombie_top_param**: top view zombie heatmap

  - Task Related Option Values
    - **--layer0-fmt <ext>** \
      The bottom layer map file format supports `jpg` or `png`. Using `jpg` can save up space at the cost of image quality. \
      Supported by: main map (top view and isometric view)

    - **--skip-level <level>** \
      Skip bottom levels of image output to save disk space and render time at the cost of a reduced max zoom level. \
      For example, Set `--skip-level 1` will omit the finest zoom level \
      Supported by: all tasks

    - **--disable-cache** \
      If present, the shared memory image cache will be disabled \
      Supported by: all tasks

    - **--cache-limit-mb** \
      The limit of shared memory can be used as cache in MB \
      Supported by: all tasks

    - **--top-color-mode** \
      Color mode for top view render. Support `avg`, `base`, `base+water` \
      Supported by: top view main map

    - **--cell-grid** \
      Enable cell grid \
      Supported by: isometric grid map

    - **--block-grid** \
      Enable block(10x10 squares) grid \
      Supported by: isometric grid map
     
    - **--cell-text** \
      Enable cell id number on the grid \
      Supported by: top view grid map

    - **--zombie-count** \
      Enable zombie density number on the heatmap \
      Supported by: isometric zombie heatmap
