
# Motivation

In [Issue 8](https://github.com/cff29546/pzmap2dzi/issues/8), it shows that creating hardlinks for duplicate images could save disk space.

However, using rdfind for deduplication has two key drawbacks:

* Performance: The first pass of rdfind compares the first byte of files, which is inefficient for pzmap2dzi scenarios where tiles are images with identical headers.

* Incremental Updates: After rendering a new mod map, rerunning rdfind to deduplicate across mod and base maps becomes prohibitively slow.

By performing deduplication at render time (instead of post-processing with rdfind), we can:

* Reduce peak disk space usage.

* Support incremental updates efficiently via a persistent file-to-hash mapping.

# Design Choices
## Hash Function

We require a **fast**, **non-cryptographic hash function** with a low collision probability. Candidates include:

* [xxHash](https://xxhash.com/): Widely supported, including in Python.

* [Meow hash](https://github.com/cmuratori/meow_hash): High performance but lacks official Python bindings.

Implementation:

* Allow users to configure the hash function. Example:

```yaml
    dedup_with_hardlink: true
    dedup_hash_function: "xxhash.xxh64"
```
* Future-proof by abstracting the hash function (e.g., switching to Meow Hash if Python support is added).


## Mapping Storage Requirements

* Shared Storage: Track file-to-hash mappings across renders.

* Concurrency: Support multi-threaded access during rendering.

* Consistency: Prevent race conditions via CRUD algorithms.

* Persistence: Survive across rendering sessions.

* Collision Handling: Detect and store hash collisions.

* Tile labeling (Optional): Label tiles (e.g., "incomplete" tiles).

## Database Design

### Schema

```sql
-- mapping_table
hash BLOB,         -- Hash value (configurable size, stored as BLOB)
id INTEGER,        -- Unique ID within a hash group (hash + id is unique)
path TEXT,         -- File path or composite key (e.g., map_type, x, y, layer, level)
inode BLOB,        -- Filesystem inode (e.g., 64/128-bit, stored as BLOB)
state INTEGER      -- Additional flags (e.g., incomplete, deleted)
```

```sql
-- meta_table
hash_algorithm TEXT,     -- e.g., "xxhash.xxh64"
collision_count INTEGER, -- Statistics
last_updated TIMESTAMP   -- Timestamps for auditing
```

### Concurrency Control


#### Insert Algorithm (New Tile Rendering)

1. Render the tile image in memory.
2. Compute its `hash_value`.
3. Query the database for `current_id`:
   * Set `current_id` to the result of `SELECT MAX(id) FROM mapping_table WHERE hash = {hash_value};`
   * If no records exist, set `current_id = 0`.
4. Insert a new record with `id = current_id + 1` and `inode = -1` (pending write).
   * Retry step 3 on unique constraint violations (race condition).
5. Check Collisions:
   * Wait for all pending writes (`inode = -1`) with lower IDs to resolve.
   * Compare the new image against existing inodes byte-for-byte.
6. Deduplicate or Write:
   * If a matching inode exists, create a hardlink.
   * If not, write the image to disk and update the inode.

If step 5 or 6 failed access inodes, retry step 5

#### Delete Algorithm (Overwriting a Tile)

1. Find the target record (by path or inode).
2. Unlink the file to break hardlinks.
3. Update the database:
   * Set `inode = 0` (deleted) or remove the record.

#### Update State
1. Fetch the record (by path or inode).
2. Modify the state field (race-free).

## Rationale

* Why Database Over Filesystem?
   * Atomic operations and transactions ensure consistency across threads.
   * Efficient querying for hashes, paths, and inodes.
* Byte-by-Byte Comparison: Safeguard against hash collisions.
* Using BLOB type for Inode: Handle filesystems with 128-bit inodes (e.g., ReFS).

