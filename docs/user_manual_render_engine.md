# Render Engine User Manual

## Requirement

Project Zomboid features an expansive map, which requires a significant amount of disk space for storage. Additionally, a powerful CPU and ample memory are essential to enhance the rendering process and minimize generation time.

Suggested minimum resources (practical baseline):
- Top view only: 8 GB RAM and 2 GB free disk space.
- Isometric base map: 32 GB RAM and 500 GB free disk space (1 TB recommended for safety).

For performance benchmarks, memory usage, and test environment details, see [Render Engine Performance Reference](./render_performance.md).

## Install Environment
1. Install [Python](https://www.python.org/downloads/)
2. Clone or download the project
3. Install requirements
    - If your Python version is 2.7, install VCForPython27 first. You can find it [here](https://web.archive.org/web/20210106040224/https://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi) or [here](https://github.com/reider-roque/sulley-win-installer/blob/master/VCForPython27.msi)
    - run `install_requirements.bat`

## Configuration
1. Update variables in the `conf/conf.yaml` file
    - Change the `pz_root` variable to the ProjectZomboid game location on your computer
    - Change the `output_path` variable to the desired output path
    - Change the `mod_root` variable to steam workshop path if you want to render a mod map
    - Add desired mod maps to the `mod_maps` list (For more info about how to add mod maps see [adding mod maps](./adding_mod_maps.md))
    - Update `render_conf`. See comments on `conf/conf.yaml` for more details
        - For example: setting `enable_cache` to `true` will turn on shared memory image cache acceleration
        - **Note on shared memory image cache acceleration:**
            - may not be compatible with [Hybrid Architecture](https://www.intel.com/content/www/us/en/developer/articles/technical/hybrid-architecture.html) CPUs
            - require Python 3.11.1 or later as earlier builds are unstable because of [buggy implementation](https://stackoverflow.com/questions/65968882/unlink-does-not-work-in-pythons-shared-memory-on-windows)

    - You can also use `scripts/gen_example_conf.py` to generate some configuration examples.

2. Change render tasks
    - Edit `run.bat` or `run_top_view_only.bat` to remove unwanted overlay tasks. For example:
        - Remove arguments `zombie` and `zombie_top` will disable the zombie heatmap
        - Remove arguments `foraging` and `foraging_top` will disable the foraging zone map

3. Start Render
   - Run `run.bat` (isometric + top view) or `run_top_view_only.bat` to start render engine

## Save Game Render

Save game rendering generates map tiles based on your local save files.

1. Requirement
    - Save game rendering only supports Python 3.x.

2. Configure save paths in `conf/conf.yaml`
    - Configure `pz_root`, `output_path` and `render_conf` as mentioned in the [Configuration section](#configuration).
    - Configure `mod_root` and `mod_maps` as mentioned in the [Configuration section](#configuration) if you want to render a mod map save.
    - Set `save_game_root` to your Project Zomboid save directory. (e.g. `%UserProfile%/zomboid/Saves` for Windows.)
    - Set `save_games`:
        - Use a list for specific saves, for example `Apocalypse/2026-02-26_15-11-44`.
        - Or set `save_games: all` to automatically render all saves that match the base map version.

3. Configure save parser
    - `render_conf.save_game_parser_tag: latest` downloads latest [pzdataspec](https://github.com/cff29546/pzdataspec) parser (default).
    - `render_conf.save_game_parser_tag: local` uses a local parser from `render_conf.save_game_parser_path`.

4. Start save rendering
    - Run `run_saves.bat`.
    - This runs `deploy`, `unpack`, then `render save save_top`.

5. Output location
    - Save render output is generated under:
      `output_root/html/map_data/saves/<save_folder>/base` and `output_root/html/map_data/saves/<save_folder>/base_top`.

