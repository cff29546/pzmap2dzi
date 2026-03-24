# Render Engine Performance Reference

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