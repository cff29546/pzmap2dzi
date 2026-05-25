from __future__ import print_function
import shutil
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


class ProgressDisplay(object):
    def __init__(self, template, finish_template=None):
        self.template = template
        self.finish_template = finish_template
        self.last_length = 0

    def _update(self, template, **kwargs):
        if not template:
            # convert falsey template to empty string to ensure format won't fail
            template = ''
            if self.last_length == 0:
                return
        text = template.format(**kwargs)
        current_length = len(text)
        if self.last_length > current_length:
            text = text.ljust(self.last_length)
        print(text, end='\r')
        self.last_length = current_length

    def update(self, **kwargs):
        self._update(self.template, **kwargs)

    def finish(self, **kwargs):
        template = self.template if self.finish_template is None else self.finish_template
        self._update(template, **kwargs)
        if template or self.last_length > 0:
            print()
            self.last_length = 0


class SimpleLock(object):
    """Atomic per-key mutex using directory creation.

    Usage (manual acquire/release):
        lock = SimpleLock(lock_path)
        while True:
            if lock.acquire():
                try:
                    # exclusively own this key; do work here
                finally:
                    lock.release()
                break
            else:
                # failed to acquire lock; another process owns it
                time.sleep(1)

    Usage (with statement syntax):
        with SimpleLock(lock_path) as locked:
            if locked:
                # exclusively own this key; do work here

    `lock_path` is the path to be atomically created. Its parent must exist

    CAUTION: This simple method is potentially unsafe.
        If the process that owns the lock crashes or fails to release it
        there will be no automatic release and resulting DEADLOCK.
        Manual cleanup will be required to remove the lock directory to recover.
    """

    def __init__(self, lock_path):
        self.lock_path = lock_path
        self.acquired = False

    def acquire(self):
        if not ensure_folder(os.path.dirname(self.lock_path)):
            return False
        if self.acquired:
            return True
        try:
            os.mkdir(self.lock_path)
            self.acquired = True
        except OSError:
            # failed to acquire lock; permissions/io issues, or another process owns it
            self.acquired = False
        return self.acquired

    def release(self):
        if self.acquired:
            try:
                os.rmdir(self.lock_path)
            except Exception:
                # failed to release lock (permissions, io, etc);
                # potentially unrecoverable DEADLOCK;
                print('WARNING: Failed to release lock at {}'.format(self.lock_path))
            self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()

def primitive_copy_file(src, dst):
    pid = os.getpid()
    dst_dir = os.path.normpath(os.path.dirname(dst))
    dst_base = os.path.basename(dst)
    tmp_base = '{}.tmp.{}'.format(dst_base, pid)
    tmp_path = os.path.join(dst_dir, tmp_base)
    success = True
    try:
        ensure_folder(dst_dir)
    except Exception as e:
        success = False
    if success:
        try:
            shutil.copyfile(src, tmp_path)
        except Exception as e:
            success = False
    if success:
        try:
            os.rename(tmp_path, dst)
        except Exception as e:
            success = False
    # cleanup tmp file if it still exists
    if os.path.isfile(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception as e:
            pass
    return success
