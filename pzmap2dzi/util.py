import struct
import os
import re
import json


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
        except Exception as e:
            pass
    if not os.path.isdir(path):
        return False
    return True


def scan_folder(path, pattern, fields=('x', 'y'), hash_func=None):
    result = {}
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    for filename in os.listdir(path):
        m = pattern.match(filename)
        if not m:
            continue
        key = tuple(map(int, m.group(*fields)))
        mtime = os.path.getmtime(os.path.join(path, filename))
        hash = None
        if hash_func:
            hasher = hash_func()
            with open(os.path.join(path, filename), 'rb') as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    hasher.update(chunk)
            hash = hasher.hexdigest()
        result[key] = (mtime, hash)
    return result


def save_json_compact(path, data):
        # dump and compact list values
        raw = json.dumps(data, indent=1)
        level = 0
        output = []
        for c in raw:
            if c == '[':
                level += 1
            elif c == ']':
                level -= 1
            elif c in ' \n':
                if level:
                    continue
            elif c == ',':
                output.append(', ')
                continue
            output.append(c)
        with open(path, 'w') as f:
            f.write(''.join(output))


def load_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)


def dict_diff(left, right, keys=None, left_name='left', right_name='right'):
    if keys is None:
        keys = set(left.keys()) | set(right.keys())
    mismatch = []
    for key in keys:
        if left.get(key) != right.get(key):
            mismatch_info = '{}: {}={}, {}={}'.format(
                key, left_name, left.get(key), right_name, right.get(key))
            mismatch.append(mismatch_info)
    return mismatch


class CoordMap(object):
    def __init__(self, map_dict, metadata=None):
        self.map = map_dict
        self.metadata = metadata or {}


def save_coord_map(path, coord_map):
    serializable = []
    for coord, data in coord_map.map.items():
        serializable.append([coord, data])
    if coord_map.metadata:
        serializable.append(['__metadata__', coord_map.metadata])
    with open(path, 'w') as f:
        json.dump(serializable, f)


def load_coord_map(path):
    if not os.path.isfile(path):
        return CoordMap({})
    coord_map = {}
    serialized = []
    with open(path, 'r') as f:
        serialized = json.load(f)
    for coord, data in serialized:
        if coord == '__metadata__':
            metadata = data
            continue
        key = tuple(coord) if isinstance(coord, list) else coord
        coord_map[key] = data
    return CoordMap(coord_map, metadata)
