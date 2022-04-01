from __future__ import print_function
import multiprocessing
try:
   import queue
except ImportError:
   import Queue as queue
try:
    from . import hotkey
except:
    hotkey = None

class Worker(object):
    def __init__(self, func, data, wid, out_q):
        self.func = func
        self.data = data
        self.wid = wid
        self.q = multiprocessing.Queue()
        self.out_q = out_q
        self.p = None

    def start(self):
        if not self.p:
            p = multiprocessing.Process(target=self._run)
            p.start()
            self.p = p

    def _run(self):
        while True:
            self.out_q.put(self.wid)
            job = self.q.get()
            if job == 'stop':
                break
            self.func(self.data, job)

    def push(self, job):
        self.q.put(job)

    def stop(self):
        self.q.put('stop')
        if self.p:
            self.p.join()
            self.p = None

def split_list(a, n):
    k, m = divmod(len(a), n)
    return [a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]

def rebalance(splits, slot):
    if len(splits[slot]) != 0:
        return splits
    
    idx = None
    maxlen = 0
    for i, jobs in enumerate(splits):
        if len(jobs) > 0:
             maxlen = len(jobs)
             idx = i
    if idx is not None:
        jobs = splits[idx]
        mid = (len(jobs) + 1) // 2
        splits[idx] = jobs[mid:]
        splits[slot] = jobs[:mid]


class Task(object):
    def __init__(self, func, data, n):
        self.func = func
        self.data = data
        self.n = n
        self.q = multiprocessing.Queue()

    def run(self, jobs, verbose=False, break_key=None):
        if len(jobs) == 0:
            if verbose:
                print('Nothing to do!')
            return True
        if len(jobs) == 1:
            if verbose:
                print('job: 0/1 worker: 1/1', end='\r')
            self.func(self.data, jobs[0])
            if verbose:
                print('job: 1/1 worker: 0/1')
            return True
        workers = []
        for i in range(min(self.n, len(jobs))):
            w = Worker(self.func, self.data, i, self.q)
            w.start()
            workers.append(w)
        hk = None
        if break_key and hotkey:
            hk = hotkey.listener([break_key])

        splits = split_list(jobs, len(workers))
        working = len(workers)
        if verbose:
            total = len(jobs)
            done = -working
        stop = False
        while working > 0:
            wid = self.q.get()
            if hk and hk.peek():
                stop = True
            if len(splits[wid]) == 0:
                rebalance(splits, wid)
            if not stop and splits[wid]:
                job = splits[wid].pop()
                workers[wid].push(job)
            else:
                workers[wid].stop()
                working -= 1
            if verbose:
                done += 1
                if done >= 0:
                    print('job: {}/{} worker: {}/{}   '.format(done, total, working, len(workers)), end='\r')
        if verbose:
            print('')
        return not stop






        



