
# Base Map and Mod Maps
You can config only one base map. But you can config many mod maps as switchable overlays.
To config the base map, put the map name in the `base_map` variable in `conf.yaml`. In the default `map_data.yaml` config, `default` is the map name for the vanilla game (i.e. Muldraugh, KY)
To config overlay mod maps, put the map names in the `mod_maps` list variable in `conf.yaml`.

# Textures
Some maps may need extra textures. To config an extra texture pack, you need to download the texture pack and config its location in the `textures` section in `map_data.yaml`

- Each texture pack has a sub-section named after the texture's name.
- The sub-section has three variables
    - `texture_root` indicate where the root path is stored in `conf.yaml`. For steam workshop texture packs, use `mod_root`
    - `texture_path` indicate the texture folder relative path from the root path
    - `texture_file_patterns` or `texture_files` indicate which texture pack(s) file under the texture folder is used. 
        - `texture_file_patterns` is a list of regular expressions that match the texture file names
        - `texture_files` the exact file name list

# Maps
Maps are defined in the `maps` section in `map_data.yaml`

- Each map has a sub-section named after the map's name
- The sub-section has several variables
    - `map_root` indicate where the root path is stored in `conf.yaml`. Similar to `texture_root` in texture section.
    - `map_path` indicate the map folder relative path from the root path
    - `encoding` indicate the text encoding used by the map, useful for room overlay. Try `utf8` when it is unknown.
    - optional texture-related variables which indicate private textures used by the map
        - similar to the texture config, it has `texture_root`, `texture_path`, `texture_files`/`texture_file_patterns`

    - `depend_textures` (optional), a list of texture names it depends
        - When depend on other map's private textures, you can also put that map's name in the list. For example, you can put `default` to use the vanilla textures.
    
# Example
A mod map named `MapName1` using vanilla textures and two extra textures named `TextureName1` and `TextureName2` rendered as an overlay. And the vanilla map is used as the base map.

- `map_data.yaml`
```
textures:
    TextureName1:
        texture_root: mod_root
        texture_path: |-
            2337452747\mods\Diederiks_tile_Palooza\media\texturepacks
        texture_file_patterns: ['.*[.]pack']

    TextureName2:
        texture_root: mod_root
        texture_path: |-
            2384329562\mods\tkTiles_01\media\texturepacks
        texture_files:
            - tkTiles_01.pack

maps:
    default:
        ...

    MapName1:
        map_root: mod_root
        map_path: |-
            1516836158\mods\FortRedstone\media\maps\FortRedstone
        encoding: utf8
        depend_texutres:
            - default
            - TextureName1
            - TextureName2
        texture_root: mod_root
        texture_path: |-
            1516836158\mods\FortRedstone\media\texturepacks
        texture_file_patterns: ['.*[.]pack']

```
- `conf.yaml`
```
...

mod_root: |- # steam workshop folder for project zomboid
    D:\SteamLibrary\steamapps\workshop\content\108600

...

base_map: default
mod_maps:
    - MapName1

...
```

# Map Compatibility
See [tested maps](./tested_maps.md)

