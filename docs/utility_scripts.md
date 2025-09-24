# Utility Scripts User Manual
This manual describes the purpose and usage of the utility scripts found in the scripts directory of the project.

## Helper Scripts for Render Configuration

These scripts facilitate the setup and management of render configurations for mod maps and tiles. They automate processes like integrity verification, dependency collection, and configuration file generation.

All scripts in this section are found in the `/scripts/` directory:

1. check_tiles.py
Purpose:
Checks the integrity and validity of map tiles. Useful for verifying that all required tiles are present and correctly formatted.

Usage:
```
python check_tiles.py [-c <conf.yaml file path>]

Options:
    -c  Path to the main configuration YAML file (default: uses internal default).
```

2. get_mod_dep.py
Purpose:
Fetches mod map dependencies from the Steam Workshop page. This script is typically used by `collect_mod_map_data.py` to gather required mod information.

Usage:
```
python get_mod_dep.py <mod id 1> <mod id 2> ...
```

3. collect_mod_map_data.py
Purpose:  
Aggregates data for all installed mod maps by retrieving information from Steam Workshop pages. It compiles mod map details and generates a render configuration for mod maps.

Usage:
```
python collect_mod_map_data.py [-c <conf.yaml file path>] [-o <output path>] [-g] [-d <dependency config 1> -d <dependency config 2> ...]

Options:
    -c  Path to the main configuration YAML file (default: uses internal default).
    -o  Output path for the generated config. (default: ./output)
    -g  Fetch unresolved dependencies from Steam.
    -d  Specify a config file with resolved dependencies (useful for incremental updates).
```

4. gen_example_conf.py
Purpose:
Generates sample configuration files using the default configuration. Primarily used for unit testing.

# Marks Generation Scripts

Scripts for generating map marks are found in the `/scripts/marks/` directory:

1. animal_tracks.py  
Extracts animal track information from map files and generates marker data compatible with the web viewer.

Usage:
```
python animal_tracks.py [-c <conf.yaml file path>] [-o <output file path>]

Options:
    -c, --conf    Path to the main configuration YAML file (default: uses internal default).
    -o, --output  Output file path for the generated animal tracks data (default: ./animal_tracks.json).
```

2. locate_texture.py
Purpose:  
Identifies specific textures utilized in map files and exports their locations as marker data compatible with the web viewer.

Usage:
```
python locate_texture.py [-c <conf.yaml file path>] [-p <parallel jobs>] [-o <output file path>] [-z <zoom limit>] <texture1> <texture2> ...

Options:
    -c, --conf           Path to the main configuration YAML file (default: uses internal default).
    -p, --parallel       Number of parallel jobs for processing (default: 16).
    -o, --output         Output file path for the generated texture location data (default: ./output.json).
    -z, --no-zoom-limit  If the number of found locations exceeds this value, all markers will only be visible at higher zoom levels (default: 128).
    textures             List of texture names to locate.
```

3. random_basement.py
Purpose:
Extracts locations of random basement entries from game data and generates marker data compatible with the web viewer.

Usage:
```
python animal_tracks.py [-c <conf.yaml file path>] [-o <output file path>]

Options:
    -c, --conf    Path to the main configuration YAML file (default: uses internal default).
    -o, --output  Output file path for the generated basement entry data (default: ./basement.json).
```

4. stash_maps.py
Purpose:
Extracts stash map locations and corresponding in-game regions from game data, generating marker data compatible with the web viewer.

Usage:
```
python animal_tracks.py [-c <conf.yaml file path>] [-o <output file path>]

Options:
    -c, --conf    Path to the main configuration YAML file (default: uses internal default).
    -o, --output  Output file path for the generated marker data (default: ./stash_maps.json).
```