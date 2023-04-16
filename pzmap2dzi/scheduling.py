from __future__ import print_function
from PIL import Image
import sys
import time
import datetime
from . import mptask, lru, util
try:
    from . import shared_memory_image
except:
    shared_memory_image = None
try:
    from . import hotkey
except:
    hotkey = None

def zorder(x, y):
    block = 1
    bit = 1
    idx = 0
    m = max(x, y)
    while bit <= m:
       if bit & x:
          idx |= block
       block <<= 1
       if bit & y:
          idx |= block
       block <<= 1
       bit <<= 1
    return idx

def zorder_key_func(arg):
    level, x, y = arg
    return -level, zorder(x, y)

def depend_task(level, x, y):
    return [(level + 1, i + (x << 1), j + (y << 1))
            for i in (0, 1) for j in (0, 1)]

class TopologicalDziScheduler(object):
    def __init__(self, dzi, stop_key=None, verbose=False):
        self.verbose = verbose
        self.cache_limit = dzi.cache_limit
        self.dzi = dzi
        self.image_size = 4 * (dzi.tile_size ** 2)
        self.cache_size = self.cache_limit * 1024 * 1024 // self.image_size
        self.cache_used = 0
        self.cache_max = 0
        self.hk = None
        if stop_key and hotkey:
            self.hk = hotkey.listener([stop_key])

    def info(self):
        if self.verbose:
            info = 'job: {}/{} '.format(self.done, self.total)
            info += 'worker: {}/{} '.format(sum(self.active), self.n)
            if self.dzi.cache_enabled:
                mb = self.image_size * self.cache_used / 1024 / 1024
                info += 'cache: {:.2f} '.format(mb)
                if self.cache_limit:
                    info += ' / {} '.format(self.cache_limit)
                info += 'MB'
            info += '    '
            print(info, end='\r')

    def release_cache(self, workers, key, method):
        if key:
            hit_key, value = self.lru.pop(key)
        else:
            hit_key, value = self.lru.pop()
        if hit_key:
            wid, layer_map = value
            worker = workers[wid]
            if worker:
                worker.push_msg((method, hit_key))
            self.cache_used -= sum(layer_map)

    def init(self, task_info, n):
        self.start_time = time.time()
        self.stop = False
        if self.verbose:
            print('Planning tasks')
        self.n = n
        self.active = [1] * n
        self.gets = [0] * n
        self.hits = [0] * n
        self.last_job = [None] * n
        tasks, done = task_info
        self.total = 0
        self.done = 0
        open_task = []
        self.dep = {}
        self.done_task = set()
        for level, task in enumerate(done):
            self.total += len(task)
            self.done += len(task)
            for x, y in task:
                self.done_task.add((level, x, y))
        for level, task in enumerate(tasks):
            self.total += len(task)
            for (x, y), depends in task.items():
                if depends == 0:
                    open_task.append((level, x, y))
                else:
                    self.dep[(level, x, y)] = depends

        open_task = sorted(open_task, key=zorder_key_func)
        self.splits = mptask.split_list(open_task, n)
        self.lru = lru.LRU()
        if self.verbose:
            print('Working')
        return True

    def on_result(self, workers, wid, state, result):
        if state == 'result':
            if result[0] == 'hold':
                hold, mem_size, gets, hits = result
                self.active[wid] = 0
                self.gets[wid] = gets
                self.hits[wid] = hits
            else:
                self.done += 1
                if self.dzi.cache_enabled:
                    level, tx, ty, layer_map = result
                    key = level, tx, ty
                    self.lru.save(key, (wid, layer_map))
                    self.cache_used += sum(layer_map)
                    if self.cache_used > self.cache_max:
                        self.cache_max = self.cache_used
                    if level == 0:
                        self.release_cache(workers, key, 'save')
                    for key in depend_task(level, tx, ty):
                        self.release_cache(workers, key, 'drop')

                    while self.cache_size and self.cache_used > self.cache_size:
                        self.release_cache(workers, None, 'save')
        self.info()
            
    def get_layer_maps(self, job):
        level, x, y = job
        if level == self.dzi.levels - 1:
            return None
        layer_maps = []
        for key in depend_task(*job):
            hit, value = self.lru.find(key)
            if hit:
                _, lm = value
            else:
                if key in self.done_task:
                    lm = [1] * self.dzi.layers
                else:
                    lm = [0] * self.dzi.layers
            layer_maps.append(lm)
        return layer_maps

    def on_empty(self, workers, wid, state, result):
        if self.stop:
            return None
        if state == 'error':
            print('worker[{}] error[{}]'.format(wid, result))
            self.stop = True
            return None
        if self.hk and self.hk.peek():
            self.stop = True
            return None
        job = 'hold'
        if state == 'ready' and len(self.splits[wid]) > 0:
            job = self.splits[wid].pop()
        if state in 'result':
            if result[0] == 'hold':
                return None if result[1] == 0 else 'hold'
            level, x, y, layer_map = result
            self.done_task.add((level, x, y))
            if level:
                key = level - 1, x >> 1, y >> 1
                self.dep[key] -= 1   
                if self.dep[key] == 0:
                    del self.dep[key]
                    self.splits[wid].append(key)
            if len(self.splits[wid]) == 0:
                mptask.rebalance(self.splits, wid)
            if len(self.splits[wid]) > 0:
                job = self.splits[wid].pop()

        if job != 'hold':
            job = job + (self.get_layer_maps(job),)
        self.last_job[wid] = job
        return job
            
    def cleanup(self): 
        self.hk = None
        self.active = [0]
        self.info()
        print('')
        print('time used', str(datetime.timedelta(0, time.time() - self.start_time)))
        if self.dzi.cache_enabled:
            mb = self.image_size * self.cache_max / 1024 / 1024
            print('cache max used: {:.2f} MB'.format(mb))
            gets = sum(self.gets)
            if gets:
                hits = sum(self.hits)
                print('cache hit: {}/{} = {:.2f}%'.format(hits, gets, 100*hits/gets))

def get_index(level, x, y, layer):
    return '{}_{}_{}_{}'.format(level, x, y, layer)

class ImageCreater(object):
    def __init__(self, mem, index, size):
        self.mem = mem
        self.index = index
        self.size = size
        self.im = None

    def get(self):
        if self.im is None:
            if self.mem is None:
                self.im = Image.new('RGBA', self.size)
            else:
                self.im = self.mem.create(self.index, *self.size)
        if self.im is None:
            raise Exception('cannot create im')
        return self.im

    def is_created(self):
        return self.im is not None

class CacheLoader(object):
    def __init__(self, mem, size):
        self.mem = mem
        self.size = size
        self.cached = set()
        self.gets = 0
        self.hits = 0

    def get(self, level, x, y, layer):
        self.gets += 1
        if self.mem is None:
            return None
        index = get_index(level, x, y, layer)
        im = self.mem.load(index, *self.size)
        if im:
            self.hits += 1
            self.cached.add(index)
        return im

    def cleanup(self):
        if self.mem is not None:
            for index in self.cached:
                self.mem.release(index)
            self.cached = set()

class TopologicalDziWorker(object):
    def __init__(self, dzi, prefix, render):
        if dzi.cache_enabled and shared_memory_image:
            self.mem = shared_memory_image.ImageSharedMemory(prefix)
        else:
            self.mem = None
        self.cache_map = {}
        self.render = render
        self.dzi = dzi
        self.gets = 0
        self.hits = 0

    def init(self):
        return True

    def on_msg(self, msg):
        if self.mem is None:
            return
        cmd, key = msg
        level, x, y = key
        for layer in range(self.dzi.layers):
            index = get_index(level, x, y, layer)
            state = self.cache_map.pop((level, x, y, layer), 'empty')
            if state == 'empty':
                continue
            if cmd == 'save' and state == 'skip':
                im = self.mem.load(index)
                self.dzi.save_tile(im, level, x, y, layer, force=True)
                im = None
            self.mem.release(index)
             
    def on_job(self, job):
        if job == 'hold':
            time.sleep(0.1)
            mem_size = len(self.cache_map)
            return 'hold', mem_size, self.gets, self.hits
        level, x, y, sub_layer_maps = job
        size = (self.dzi.tile_size, self.dzi.tile_size)
        is_base = (level == self.dzi.levels - 1)
        cl = CacheLoader(self.mem, size)
        layer_map = [0] * self.dzi.layers
        self.dzi.set_wip(level, x, y)
        for layer in reversed(range(self.dzi.layers)):
            index = get_index(level, x, y, layer)
            ic = ImageCreater(self.mem, index, size)
            if is_base:
                self.dzi.render_tile(ic, self.render, x, y, layer)
            else:
                cached = []
                for pos, (sub_level, sub_x, sub_y) in enumerate(depend_task(level, x, y)):
                    if sub_layer_maps[pos][layer] == 0:
                        cached.append('empty')
                    else:
                        im = cl.get(sub_level, sub_x, sub_y, layer)
                        cached.append(im)
                self.dzi.merge_tile(ic, level, x, y, layer, cached)
                cached = []
            im = None
            if ic.is_created():
                im = ic.get()
            force = self.mem is None
            state = self.dzi.save_tile(im, level, x, y, layer, force)
            ic = None
            im = None
            if state == 'empty':
                if self.mem is not None:
                    self.mem.release(index)
                if layer == 0 and sum(layer_map) > 0:
                    self.dzi.mark_empty(level, x, y, 0)
            else:
                if self.mem is not None:
                    self.cache_map[(level, x, y, layer)] = state
                layer_map[layer] = 1
        self.gets += cl.gets
        self.hits += cl.hits
        cl.cleanup()
        self.dzi.clear_wip(level, x, y)
        return level, x, y, layer_map
        




