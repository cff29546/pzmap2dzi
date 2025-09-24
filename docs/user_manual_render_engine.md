# Render Engine User Manual

## Requirement

Project Zomboid features an expansive map, which requires a significant amount of disk space for storage. Additionally, a powerful CPU and ample memory are essential to enhance the rendering process and minimize generation time. Please refer to the table below to ensure that you have sufficient resources for your rendering settings.

* Memory usage

|Veiw Type | Approximate Peak Memory Usage |
|:-:|:-:|
| isometric | 500 MB per Worker + 4 GB Shared |
| top | 200 MB per Worker + 200 MB Shared |

* Output size and generation time

| Game Version </th><th> B42.11.0 </th> <th> Engine Version </th> <th> [1.1.7](https://github.com/cff29546/pzmap2dzi/tree/b866ce8187f7c47890306c746bd6312cbe56622c) </th> <th> Test Environment: [Test1](#test1) </th> </tr> <tr> |  View Type </th><th> Image Format | Overlay Task | Output Size | Generation Time (h:mm:ss) |
|-|-|-|-|-|
| all | json (marks) | rooms | 12 MB | 0:00:05 |
| all | json (marks) | objects | 1 MB | 0:00:01 |
| all | json (marks) | streets | 0.25 MB | 0:00:01 |

| Game Version </th><th> B42.6.0 </th> <th> Engine Version </th> <th> [1.0.8](https://github.com/cff29546/pzmap2dzi/tree/a3f403716182e21997a5c14e6c8c8df25d9510ea) </th> <th> Test Environment: [Test1](#test1) </th> </tr> <tr> |  View Type </th><th> Image Format | Overlay Task | Output Size | Generation Time (h:mm:ss) |
|-|-|-|-|-|
| isometric | webp | base | 404 GB | 12:45:54 |
| isometric | webp (with jpg ground floor) | base | 347 GB | 3:36:04 |
| isometric | webp | zombie heatmap | 369 MB | 0:16:55 |
| isometric | webp | foraging | 6.2 GB | 5:22:34 |
| isometric | webp | rooms | 927 MB | 1:02:05 |
| isometric | webp | objects | 331 MB | 0:25:23 |
| top | webp | base | 67 MB |0:52:41 |
| top | webp | zombie heatmap | 2.6 MB | 0:00:08 |
| top | webp | foraging | 11 MB | 0:00:56 |

| Game Version </th><th> B41.78.16 </th> <th> Engine Version </th> <th> [1.0.8](https://github.com/cff29546/pzmap2dzi/tree/a3f403716182e21997a5c14e6c8c8df25d9510ea) </th> <th> Test Environment: [Test1](#test1) </th> </tr> <tr> |  View Type </th><th> Image Format | Overlay Task | Output Size | Generation Time (h:mm:ss) |
|-|-|-|-|-|
| isometric | webp | base | 431 GB | 12:05:54 |
| isometric | webp (with jpg ground floor) | base | 369 GB | 3:01:15 |
| isometric | webp | zombie heatmap | 4.8 GB | 4:05:13 |
| isometric | webp | foraging | 1.9 GB | 1:28:14 |
| isometric | webp | rooms | 772 MB | 0:25:44 |
| isometric | webp | objects | 231 MB | 0:10:12 |
| top | webp | base | 64 MB | 0:11:44 |
| top | webp | zombie heatmap | 6.9 MB | 0:00:11 |
| top | webp | foraging | 4.8 MB | 0:00:43 |

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

## Test Environment

### Test1
- CPU: AMD Ryzen 7 5700G @ 3.8 GHz (8 cores, 16 threads)
- Memory: 128GB DDR4 3600 Dual Channels
- Output Storage: NVME SSD
- OS: Windows 10 Enterprise LTSC 21H2 (19044.5608)
- File System: NTFS on virtual disk
    - use a dynamic `.vhd` (or `.vhdx` for more than 2TB output) virtual disk on the hosting drive for output
    - the virtual disk is provisioned with a single partition
- Module Version:
    - python: 3.12.1
    - pillow: 11.1.0
- Render Settings:
    - 16 worker threads
    - shared memory image cache acceleration enabled

