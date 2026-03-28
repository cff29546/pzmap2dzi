import struct
import os
import re


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