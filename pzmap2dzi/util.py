import struct
import os
import re

HEADER_FILE_PATTERN = re.compile('(\\d+)_(\\d+)\\.lotheader$')
def get_all_cells(path):
    cells = []
    for f in os.listdir(path):
        m = HEADER_FILE_PATTERN.match(f)
        if not m:
            continue

        x, y = map(int, m.groups())
        cells.append((x, y))
    return cells


PENDING_PATTERN = re.compile('(\\d+)_(\\d+)\\.pending$')
TILE_PATTERN = re.compile('(\\d+)_(\\d+)\\.png$')
DONE_PATTERN = re.compile('(\\d+)_(\\d+)\\.(?:empty|png)$')
def get_done_tiles(path):
    if not os.path.isdir(path):
        return set()
    done = set()
    pending = set()
    for f in os.listdir(path):
        m = DONE_PATTERN.match(f)
        if m:
            x, y = map(int, m.groups())
            done.add((x, y))
            continue
        m = PENDING_PATTERN.match(f)
        if m:
            x, y = map(int, m.groups())
            pending.add((x, y))
    return done - pending

def set_empty(path, x, y):
    with open(os.path.join(path, '{}_{}.empty'.format(x, y)), 'w') as f:
        pass

def set_wip(path, x, y):
    with open(os.path.join(path, '{}_{}.pending'.format(x, y)), 'w') as f:
        pass

def clear_wip(path, x, y):
    os.remove(os.path.join(path, '{}_{}.pending'.format(x, y)))

def read_until(data, pos, pattern):
    end = data.index(pattern, pos) + len(pattern)
    return data[pos: end], end

def read_line(data, pos):
    line, pos = read_until(data, pos, b'\n')
    return line[:-1], pos

def read_uint8(data, pos):
    return struct.unpack('B', data[pos: pos+1])[0], pos + 1

def read_uint32(data, pos):
    return struct.unpack('I', data[pos: pos+4])[0], pos + 4

def read_int32(data, pos):
    return struct.unpack('i', data[pos: pos+4])[0], pos + 4

def read_bytes_with_length(data, pos):
    length, _ = read_uint32(data, pos)
    return data[pos + 4: pos + 4 + length], pos + 4 + length

def ensure_folder(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            pass
    if not os.path.isdir(path):
        return False
    return True
