from __future__ import print_function
import multiprocessing
import traceback
import cProfile
try:
   import queue
except ImportError:
   import Queue as queue

class WorkerWarp(object):
    def __init__(self, worker, wid, out_q, profile=False):
        self.worker = worker
        self.wid = wid
        self.profile = profile
        self.q = multiprocessing.Queue()
        self.out_q = out_q
        self.p = None

    def start(self):
        if not self.p:
            p = multiprocessing.Process(target=self._run)
            p.start()
            self.p = p

    def _run(self):
        if self.profile:
            pr = cProfile.Profile()
            pr.enable()
        if hasattr(self.worker, 'init'):
            init = False
            result = None
            try:
                init = self.worker.init()
            except Exception as e:
                print('worker:[{}] init error, Exception: {}'.format(e))
                traceback.print_exc()
                init = False
                result = e
            if not init:
                state = 'init_failed'
                self.out_q.put([self.wid, state, result])
                return
        state = 'ready'
        result = None
        while True:
            if state:
                self.out_q.put([self.wid, state, result])
            cmd, arg = self.q.get()
            if cmd == 'stop':
                break
            if cmd == 'job':
                try:
                    result = self.worker.on_job(arg)
                    state = 'result'
                except Exception as e:
                    print('job:[{}] error, Exception: {}'.format(arg, e))
                    traceback.print_exc()
                    state = 'error'
                    result = e
            if cmd == 'msg':
                try:
                    self.worker.on_msg(arg)
                except Exception as e:
                    print('msg:[{}] error, Exception: {}'.format(arg, e))
                    traceback.print_exc()
                state = None
                
        if hasattr(self.worker, 'cleanup'):
            try:
                self.worker.cleanup()
            except Exception as e:
                print('worker cleanup error, Exception: {}'.format(e))
        if self.profile:
            pr.disable()
            pr.print_stats(sort='tottime')

    def push_job(self, job):
        self.q.put(['job', job])

    def push_msg(self, msg):
        self.q.put(['msg', msg])

    def stop(self):
        self.q.put(['stop', None])
        self.join()

    def join(self):
        if self.p:
            self.p.join()
            self.p = None

# worker interface
# worker.init() -> bool
#     should return True when successful
# worker.cleanup()
#     cleanup
# worker.on_job(job) -> result
#     process job
# worker.on_msg(msg)
#     process message form scheduler, no response needed

# scheduler interface
# scheduler.init(tasks, num_processes) -> bool
#     should return True when successful
# scheduler.cleanup()
#     cleanup
# scheduler.on_result(workers, worker_id, state, result) -> info
#     callback when receiving result from worker
#     [workers] contain a list of all worker wrappers
#          workers[id].push_msg(msg) can be called to send msg to workers
#     [state] value may be one of following:
#         'ready'       worker successfully started no job processed yet
#         'init_failed' worker init failed, any exception caught will be stored in [result]
#         'result'      a job is fininshed and returend [result]
#         'error'       a job process failed, any exception caught will be stored in [result]
#     scheduler may change its inner states in this callback
#     if return value [info] is not None, it will be printed out.
# scheduler.on_empty(workers, worker_id, state, result) -> next_job
#     callback when there is a free worker ready for next_job
#     [state] value similar to on_result
#     return value [next_job] is the next_job assigned to the free worker
#            if next_job is None the free worker is stopped.
class Task(object):
    def __init__(self, worker, scheduler, profile=False):
        self.worker = worker
        self.scheduler = scheduler
        self.profile = profile
        self.q = multiprocessing.Queue()

    def run(self, tasks, num_processes):
        if hasattr(self.scheduler, 'init'):
            try:
                self.scheduler.init(tasks, num_processes)
            except Exception as e:
                print('scheduler init failed, Exception: {}'.format(e))
                traceback.print_exc()
                return False

        workers = []
        if num_processes < 1:
            num_processes = 1
        for i in range(num_processes):
            profile = self.profile and i == 0
            w = WorkerWarp(self.worker, i, self.q, profile)
            w.start()
            workers.append(w)

        working = len(workers)
        while working > 0:
            wid, state, result = self.q.get()
            if state == 'init_failed':
                working -= 1
                workers[wid].join()
                workers[wid] = None
                print('worker[{}] init failed with result[{}]'.format(wid, result))
            if state in ['result', 'error'] and hasattr(self.scheduler, 'on_result'):
                info = None
                try:
                    info = self.scheduler.on_result(workers, wid, state, result)
                except Exception as e:
                    print('scheduler error on result[{}] state[{}]. Exception {}'
                          .format(result, state, e))
                    traceback.print_exc()
                if info is not None:
                    print(info, end='')
            if state in ['ready', 'result', 'error']:
                next_job = None
                try:
                    next_job = self.scheduler.on_empty(workers, wid, state, result)
                except Exception as e:
                    print('scheduler error assigning job, result[{}] state[{}]. Exception {}'
                          .format(result, state, e))
                    traceback.print_exc()
                if next_job is not None:
                    workers[wid].push_job(next_job)
                else:
                    working -= 1
                    workers[wid].stop()
                    workers[wid] = None
        if hasattr(self.scheduler, 'cleanup'):
            try:
                self.scheduler.cleanup()
            except Exception as e:
                print('scheduler cleanup error, Exception: {}'.format(e))
                traceback.print_exc()


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
        splits[slot].reverse()

class SplitScheduler(object):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def init(self, tasks, n):
        self.splits = split_list(tasks, n)
        self.n = n
        self.total = len(tasks)
        self.done = 0
        return True

    def on_result(self, workers, wid, state, result):
        if self.verbose:
            self.done += 1
            active = sum([1 if w else 0 for w in workers])
            print('job: {}/{} worker: {}/{}       '.format(
                    self.done, self.total, active, self.n), end='\r')

    def on_empty(self, workers, wid, state, result):
        if len(self.splits[wid]) == 0:
            rebalance(self.splits, wid)
        if len(self.splits[wid]) == 0:
            return None
        return self.splits[wid].pop()

    def cleanup(self):
        if self.verbose:
            print('job: {}/{} worker: {}/{}       '.format(
                  self.done, self.total, 0, self.n))

class TestWorker(object):
    def on_job(self, job):
        import time, random
        time.sleep(random.random()) # print(job)
def test():
    worker = TestWorker()
    task = Task(worker, SplitScheduler(True))
    task.run(list(range(100)), 10)

if __name__ == '__main__':
    test()
