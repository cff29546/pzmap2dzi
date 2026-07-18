from __future__ import print_function
from PIL import Image, ImageDraw
import sys
import time
import datetime
from . import lru, mptask, util
try:
    from . import shared_memory_image
except ImportError:
    shared_memory_image = None
try:
    from . import hotkey
except ImportError:
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
        self.stop_key = stop_key
        self.image_size = 4 * (dzi.tile_size ** 2)
        self.cache_size = self.cache_limit * 1024 * 1024 // self.image_size
        self.cache_used = 0
        self.cache_max = 0
        self.hk = None

    def init(self, context, task_info):
        self.context = context
        context.set_auto_stop_worker(False)
        self.start_time = time.time()
        self.stop = False
        if self.verbose:
            print('Planning tasks')
        if self.stop_key and hotkey:
            self.hk = hotkey.listener([self.stop_key])
        n = context.coordinator.n
        self.n = n
        self.done_worker = 0
        self.active_worker = n
        self.active = [1] * n
        self.stopped = [0] * n
        self.gets = [0] * n
        self.hits = [0] * n
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

    def release_cache(self, key, method):
        if key:
            hit_key, value = self.lru.pop(key)
        else:
            hit_key, value = self.lru.pop()
        if hit_key:
            wid, layer_map = value
            if self.stopped[wid] == 0:
                self.context.send_msg(wid, (method, hit_key))
            self.cache_used -= sum(layer_map)

    def shutdown(self):
        if self.dzi.cache_enabled:
            while self.lru.count > 0:
                self.release_cache(None, 'save')
        self.context.stop_all_workers()
        if self.hk:
            self.hk.stop()
            self.hk = None

    def on_result(self, wid, job, result):
        if result[0] == 'summary':
            _, gets, hits = result
            self.done_worker += 1
            self.gets[wid] = gets
            self.hits[wid] = hits
            if self.done_worker == self.n:
                self.shutdown()
        else:
            self.done += 1
            level, x, y, layer_map = result
            self.done_task.add((level, x, y))
            key = self.get_thumbnail_task((level, x, y))
            if key is not None:
                self.dep[key] -= 1
                if self.dep[key] == 0:
                    del self.dep[key]
                    self.splits[wid].append(key)
            if self.dzi.cache_enabled:
                tx, ty = x, y
                key = level, tx, ty
                self.lru.save(key, (wid, layer_map))
                self.cache_used += sum(layer_map)
                if self.cache_used > self.cache_max:
                    self.cache_max = self.cache_used
                if self.get_thumbnail_task(key) is None:
                    self.release_cache(key, 'save')
                for key in depend_task(level, tx, ty):
                    self.release_cache(key, 'drop')

                if self.cache_size:
                    while self.cache_used > self.cache_size:
                        self.release_cache(None, 'save')

    def on_failed(self, wid, job, error):
        print('worker[{}] error[{}]'.format(wid, error))
        self.stop = 'error'
        self.shutdown()

    def get_thumbnail_task(self, key):
        level, x, y = key
        if level <= 0:
            return None
        tlevel, tx, ty = level - 1, x >> 1, y >> 1
        if (tlevel, tx, ty) in self.done_task:
            return None
        return tlevel, tx, ty

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

    def on_worker_ready(self, wid):
        if not self.active[wid]:
            return None
        if self.hk and self.hk.peek():
            self.stop = 'hotkey'

        job = 'summary'
        if not self.stop:
            if len(self.splits[wid]) == 0:
                mptask.rebalance(self.splits, wid)
            if len(self.splits[wid]) > 0:
                self.active[wid] = 1
                job = self.splits[wid].pop()
                job = job + (self.get_layer_maps(job),)
        if job == 'summary':
            self.active[wid] = 0
            self.active_worker -= 1
        return job

    def on_worker_stopped(self, wid):
        self.stopped[wid] = 1

    def update_status(self):
        if not self.verbose:
            return None
        info = 'job: {}/{} '.format(self.done, self.total)
        info += 'worker: {}/{} '.format(self.active_worker, self.n)
        if self.dzi.cache_enabled:
            mb = self.image_size * self.cache_used / 1024 / 1024
            info += 'cache: {:.2f} '.format(mb)
            if self.cache_limit:
                info += ' / {} '.format(self.cache_limit)
            info += 'MB'
        return info

    def cleanup(self):
        time_used = time.time() - self.start_time
        print('time used: {}'.format(str(datetime.timedelta(0, time_used))))
        if self.dzi.cache_enabled:
            mb = self.image_size * self.cache_max / 1024 / 1024
            print('cache max used: {:.2f} MB'.format(mb))
            gets = sum(self.gets)
            if gets:
                hits = sum(self.hits)
                rate = 100*hits/gets
                print('cache hit: {}/{} = {:.2f}%'.format(hits, gets, rate))


def get_index(level, x, y, layer):
    return '{}_{}_{}_{}'.format(level, x, y, layer)


class ImageCreater(object):
    def __init__(self, mem, index, size):
        self.mem = mem
        self.index = index
        self.size = size
        self.im = None
        self.draw = None

    def get(self):
        if self.im is None:
            if self.mem is None:
                self.im = Image.new('RGBA', self.size)
            else:
                self.im = self.mem.create(self.index, *self.size)
        if self.im is None:
            raise Exception('cannot create im')
        return self.im

    def get_draw(self):
        if self.draw is None:
            self.draw = ImageDraw.Draw(self.get())
        return self.draw

    def is_created(self):
        return self.im is not None

    def release_reference(self):
        self.im = None
        self.draw = None


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
    def __init__(self, dzi, prefix):
        if dzi.cache_enabled and shared_memory_image:
            self.mem = shared_memory_image.ImageSharedMemory(prefix)
        else:
            self.mem = None
        self.cache_map = {}
        self.dzi = dzi
        self.gets = 0
        self.hits = 0

    def init(self, context=None):
        return True

    def on_msg(self, msg):
        if self.mem is None:
            return
        cmd, key = msg
        level, x, y = key
        for layer in range(self.dzi.minlayer, self.dzi.maxlayer):
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
        if job == 'summary':
            return 'summary', self.gets, self.hits
        level, x, y, sub_layer_maps = job
        size = (self.dzi.tile_size, self.dzi.tile_size)
        is_base = (level == self.dzi.levels - 1)
        cl = CacheLoader(self.mem, size)
        layer_map = [0] * self.dzi.layers
        layer_cache = [None] * self.dzi.layers
        self.dzi.set_wip(level, x, y)
        for layer in range(self.dzi.render_minlayer, self.dzi.render_maxlayer):
            index = get_index(level, x, y, layer)
            ic = ImageCreater(self.mem, index, size)
            if is_base:
                self.dzi.render_tile(ic, x, y, layer, layer_cache)
            else:
                cached = []
                depend_tasks = depend_task(level, x, y)
                for pos, (sub_level, sub_x, sub_y) in enumerate(depend_tasks):
                    if sub_layer_maps[pos][layer] == 0:
                        cached.append('empty')
                    else:
                        cached.append(cl.get(sub_level, sub_x, sub_y, layer))
                self.dzi.merge_tile(ic, level, x, y, layer, cached)
                cached = []

            force = self.mem is None
            state = self.dzi.save_tile(ic.im, level, x, y, layer, force)

            if state == 'empty':
                if self.mem is not None:
                    ic.release_reference()
                    self.mem.release(index)
            else:
                if self.mem is not None:
                    self.cache_map[(level, x, y, layer)] = state
                layer_map[layer] = 1
            layer_cache[layer] = ic.im
            ic.release_reference()

        if not layer_map[0]:
            self.dzi.mark_empty(level, x, y, 0)
        layer_cache = None

        self.gets += cl.gets
        self.hits += cl.hits
        cl.cleanup()
        self.dzi.clear_wip(level, x, y)
        return level, x, y, layer_map
