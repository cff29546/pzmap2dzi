
# Base Map and Mod Maps
When setting up maps, keep in mind that you can only configure one base map, but you can configure multiple mod maps as switchable overlays.

To configure the base map, simply place the map name in the `base_map` variable in `conf/conf.yaml`.
To configure overlay mod maps, add the map names to the `mod_maps` list variable in `conf.yaml`.

The `map_conf` variable in the `conf/conf.yaml` file contains a list of all map description files (folders).
In the default map description file `conf/vanilla.txt`, `default` represents the map name and texture name for the vanilla game (e.g. Muldraugh, KY).

# Mod discription section
Every texture mod or map mod requires a unique description section. This section can be located in any file or folder listed in `map_conf`, but it is recommended to place additional mod sections in the `conf/mod/` folder.

# Texture section
Some maps may require additional textures. To specify an extra texture pack, please download the texture pack and describe its location in the texture section.

```
<mod_id>:
  texture: true
  mod_name: <mod_name>
  steam_id: <steam_id>
  texture_path: <texture_path_template>
  texture_files: <a list with one or more file name patterns (regex)>
```

- `<mod_id>` is the reference name for declaring dependency.
- `texture_path` is optional; if omitted, the default template is `{mod_root}/{steam_id}/mods/{mod_name}/media/texturepacks`. You can also provide an absolute path to override the `texture_path` for non-workshop textures. Template substitution uses key-value pairs from the current `<moc_id>` section and the global configuration (`conf/conf.yaml`).
- `texture_files` is optional; if omitted, it will match all `.pack` files under `texture_path`.

# Map section
Maps are defined in the map sections.

```
<mod_id>:
  texture: true
  mod_name: <mod_name>
  steam_id: <steam_id>
  map_name: <map_name>
  encoding: <encoding for map text>
  map_path: <map_path_template>
  depend: <a list with mod_id of depend textures and maps>
```

- `<mod_id>` serves as the reference name for the map.
- If the map includes self-provided textures, `texture: true` is necessary; otherwise, it can be omitted.
    - You can also utilize `texture_path` and `texture_files` like in texture sections for self-provided textures.
- `encoding` is optional; the default is `utf8`.
- `map_path`  is optional; if not included, the template `{mod_root}/{steam_id}/mods/{mod_name}/media/maps/{map_name}` will be used. You can also replace the `map_path` with an absolute path for non-workshop maps.
- `depend` is optional; if not included, only the default vanilla textures `default` will be used.

- Note: A map section can also be used as a texture section for another map to depend on.

# Map discription generation
To get map descriptions for all installed mod maps, you can use the auto-generation script.

Navigate to the `script/` folder and execute the following command:
```
collect_mod_map_data.py -g
```
Please note that this script requires access to the Steam website to retrieve mod dependencies.

The script will produce two output files, `maps-<timestamp>.txt` and `textures-<timestamp>.txt`, within the `script/` folder. After running the script, copy the output files to `conf/mod/` for further use.

Instead of accessing Steam, you can use dependencies from an existing output by the following command:
```
collect_mod_map_data.py -d <map-description-file> -d <texture-description-file>
```

# Example
A mod map called "Grapeseed" uses a combination of vanilla textures, self-provided textures, and three additional mod textures named `DylansTiles`, `Diederiks Tile Palooza`, and `tkTiles_01` overlaid on the vanilla base map.

- `conf/mod/example.txt`
```
DylansTiles:
  mod_name: DylansTiles
  steam_id: '2599752664'
  texture: true

Diederiks Tile Palooza:
  mod_name: Diederiks_tile_Palooza
  steam_id: '2337452747'
  texture: true

tkTiles_01:
  mod_name: tkTiles_01
  steam_id: '2384329562'
  texture: true

Grapeseed:
  depend:
  - DylansTiles
  - Diederiks Tile Palooza
  - tkTiles_01
  map_name: Grapeseed
  mod_name: Grapeseed
  steam_id: '2463499011'
  texture: true

```
- `conf/conf.yaml`
```
...

mod_root: |- # steam workshop folder for project zomboid
    D:/SteamLibrary/steamapps/workshop/content/108600

...

base_map: default
mod_maps:
    - Grapeseed

...
```

# Map Compatibility
See [tested maps](./tested_maps.md)

