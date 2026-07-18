
import multiprocessing
import traceback
import tempfile
import cProfile
import pstats
import os
import pickle

VERSION = '2.0.0'

LIB_NAME = '[{}] '.format(__name__)

# messages:

# READY: worker sends this message to coordinator when it's ready to receive jobs (initialization successful)
READY = 'ready'
# INIT_FAILED: worker sends this message to coordinator when initialization fails (process will exit after sending this message)
INIT_FAILED = 'init_failed'
# ERROR: worker sends this message to coordinator when an error occurs
ERROR = 'error'
# CRASH: worker sends this message to coordinator when it crashes (no longer able to receive jobs)
CRASH = 'crash'
# RESULT: worker sends this message to coordinator when a job is completed
RESULT = 'result'
# FAILED: worker sends this message to coordinator when a job fails
FAILED = 'failed'
# STOP: coordinator sends this message to worker to stop the worker process
STOP = 'stop'
# TERMINATED: worker sends this message to coordinator when it receives a stop command and is about to exit
TERMINATED = 'terminated'
# JOB: coordinator sends this message to worker to assign a job (data is the job data)
JOB = 'job'
# MSG: coordinator sends this message to worker to send a message (data is the message data)
MSG = 'msg'
# DONE: coordinator sends this message to main process to indicate that all jobs are done (only used in async mode)
DONE = 'done'

def _is_picklable(obj):
    try:
        pickle.dumps(obj)
        return True
    except Exception:
        return False


def _safe_call(func, *args):
    # return value (status, result, exception)
    # status: True: function called successfully, False: function failed with exception, None: function does not exist
    if not func:
        return None, None, None
    try:
        return True, func(*args), None
    except Exception as e:
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        print(LIB_NAME + 'Callback error, Function: {}, Exception: {}'.format(func_name, e))
        traceback.print_exc()
        return False, None, e


def _safe_call_method(obj, method_name, *args):
    # return value (status, result, exception)
    # status: True: method called successfully, False: method failed with exception, None: method does not exist
    method = getattr(obj, method_name, None)
    if not method:
        return None, None, None
    try:
        return True, method(*args), None
    except Exception as e:
        obj_name = type(obj).__name__
        print(LIB_NAME + 'Callback error, Object: {}, Method: {}, Exception: {}'.format(obj_name, method_name, e))
        traceback.print_exc()
        return False, None, e

class JobFailedException(Exception):
    def __init__(self, message):
        super().__init__(message)

class WorkerContext:
    def __init__(self, process):
        self.process = process

    def send_msg(self, msg):
        self.process._send_message(MSG, msg)


class _WorkerProcess:
    def __init__(self, worker, worker_id, coordinator_queue, profile_path):
        self.worker = worker
        self.worker_id = worker_id
        self.coordinator_queue = coordinator_queue
        self.p = None
        self.q = multiprocessing.Queue()
        self.profile_path = profile_path
        self.context = WorkerContext(self)
        self.stopping = False

    def start(self):
        if not self.p:
            p = multiprocessing.Process(target=self._worker_proc)
            p.start()
            self.p = p

    def stop(self):
        if not self.stopping:
            self.q.put((STOP, None))
        self.stopping = True

    def join(self):
        if self.p:
            self.p.join()
            self.p = None

    def _send_message(self, state, data=None):
        try:
            self.coordinator_queue.put((self.worker_id, state, data))
        except (pickle.PicklingError, TypeError, AttributeError) as e:
            # data unpicklable, send error message to coordinator
            if state in (RESULT, FAILED, ERROR):
                self.coordinator_queue.put((self.worker_id, ERROR, e))
            else:
                print(LIB_NAME + 'Worker {} failed to send message to coordinator, state: {}, Exception: {}'.format(self.worker_id, state, e))
                traceback.print_exc()

    def _worker_proc(self):
        pr = None
        if os.path.isdir(self.profile_path):
            pr = cProfile.Profile()
            pr.enable()
        status, result, error = _safe_call_method(self.worker, 'init', self.context)
        if status is False:
            self._send_message(INIT_FAILED, error)
            return
        self._send_message(READY)
        self._job_loop()
        if pr:
            pr.disable()
            dump_file = os.path.join(self.profile_path, 'worker_{}.prof'.format(self.worker_id))
            dump_file = os.path.normpath(os.path.abspath(dump_file))
            pr.dump_stats(dump_file)
        self._send_message(TERMINATED)

    def _job_loop(self):
        while True:
            try:
                cmd, arg = self.q.get()
            except Exception as e:
                print(LIB_NAME + 'Worker get command error, Exception: {}'.format(e))
                traceback.print_exc()
                self._send_message(CRASH, e)
                break
            if cmd == STOP:
                break
            elif cmd == JOB:
                state = RESULT
                status, result, error = None, None, None
                if hasattr(self.worker, 'on_job'):
                    status, result, error = _safe_call_method(self.worker, 'on_job', arg)
                else:
                    status, result, error = _safe_call(self.worker, arg)
                if status is False:
                    state = FAILED if isinstance(error, JobFailedException) else ERROR
                    result = error
                elif status is None:
                    # Missing job handler method
                    print(LIB_NAME + 'Worker error: missing job handler')
                    self._send_message(CRASH, Exception('Missing job handler'))
                    break
                self._send_message(state, result)
            elif cmd == MSG:
                _safe_call_method(self.worker, 'on_msg', arg)
        _safe_call_method(self.worker, 'cleanup')


class CoordinatorContext:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.auto_stop_worker = True

    def set_auto_stop_worker(self, auto_stop):
        self.auto_stop_worker = auto_stop

    def send_msg(self, worker_id, msg):
        return self.coordinator._send_message(worker_id, MSG, msg)

    def stop_worker(self, worker_id):
        return self.coordinator._stop_worker(worker_id)

    def stop_all_workers(self):
        for worker in range(self.coordinator.n):
            self.coordinator._stop_worker(worker)

    def assign_job(self, worker_id, job):
        return self.coordinator._assign_job(worker_id, job)

    def get_current_jobs(self, worker_id):
        return self.coordinator.current_jobs[worker_id]

class _CoordinatorProcess:
    def __init__(self, coordinator, worker, num_workers, profile_path):
        self.coordinator = coordinator
        self.worker = worker
        # Windows multiprocessing defaults to spawn, so payload objects must be picklable.
        if os.name == 'nt':
            if not _is_picklable(self.coordinator):
                raise TypeError(
                    'Coordinator object must be picklable on Windows, got type: {}'.format(
                        type(self.coordinator).__name__
                    )
                )
            if not _is_picklable(self.worker):
                raise TypeError(
                    'Worker object must be picklable on Windows, got type: {}'.format(
                        type(self.worker).__name__
                    )
                )

        self.n = num_workers
        self.profile_path = profile_path
        self.workers = []
        self.current_jobs = [[] for _ in range(num_workers)]
        self.q = multiprocessing.Queue()
        self.p = None
        self.context = CoordinatorContext(self)

    def _init_workers(self):
        for i in range(self.n):
            wp = _WorkerProcess(self.worker, i, self.q, self.profile_path)
            wp.start()
            self.workers.append(wp)
        self.working = self.n

    def start(self, tasks):
        if not self.p:
            self.sync_queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=self.run, args=(tasks, True))
            p.start()
            self.p = p

    def wait(self):
        if self.p:
            _, cleanup_result = self.sync_queue.get()
            self.p.join()
            self.p = None
            return cleanup_result

    def run(self, tasks, is_async=False):
        pr = None
        cleanup_result = None
        if os.path.isdir(self.profile_path):
            pr = cProfile.Profile()
            pr.enable()
        success, result, error = _safe_call_method(self.coordinator, 'init', self.context, tasks)
        if success is False:
            print(LIB_NAME + 'Coordinator init failed, Exception: {}'.format(error))
            traceback.print_exc()
        if success is None:
            print(LIB_NAME + 'Coordinator error: missing required callback init')
        if success is True:
            self._init_workers()
            cleanup_result = self._loop()
        if pr:
            pr.disable()
            dump_file = os.path.join(self.profile_path, 'coordinator.prof')
            dump_file = os.path.normpath(os.path.abspath(dump_file))
            pr.dump_stats(dump_file)
            stats = pstats.Stats(pr)
            for i in range(self.n):
                worker_dump_file = os.path.join(self.profile_path, 'worker_{}.prof'.format(i))
                worker_dump_file = os.path.normpath(os.path.abspath(worker_dump_file))
                if os.path.isfile(worker_dump_file):
                    stats.add(worker_dump_file)
            stats.dump_stats(os.path.join(self.profile_path, 'total.prof'))
        if is_async:
            self.sync_queue.put((DONE, cleanup_result))
        return cleanup_result

    def _send_message(self, worker_id, state, data=None):
        if worker_id < 0 or worker_id >= self.n:
            print(LIB_NAME + 'Coordinator error: worker index [{}] out of range when sending message [{}]'.format(worker_id, state))
            return False
        worker = self.workers[worker_id]
        if worker and worker.p:
            try:
                worker.q.put((state, data))
            except (pickle.PicklingError, TypeError, AttributeError) as e:
                # data unpicklable, send error message to coordinator
                print(LIB_NAME + 'Worker {} failed to send message to coordinator, state: {}, Exception: {}'.format(worker_id, state, e))
                traceback.print_exc()
                return False
            return True
        else:
            print(LIB_NAME + 'Coordinator error: worker [{}] already stopped when sending message [{}]'.format(worker_id, state))
            return False

    def _assign_job(self, worker_id, job):
        success = self._send_message(worker_id, JOB, job)
        if success:
            self.current_jobs[worker_id].append(job)
        return success

    def _stop_worker(self, worker_id):
        worker = self.workers[worker_id]
        if worker:
            worker.stop()

    def _join_worker(self, worker_id):
        worker = self.workers[worker_id]
        if worker:
            worker.join()
            self.workers[worker_id] = None
            self.working -= 1

    def _loop(self):
        status_len = 0
        while self.working > 0:
            try:
                worker_id, state, data = self.q.get()
            except Exception as e:
                print(LIB_NAME + 'Coordinator get message error, Exception: {}'.format(e))
                traceback.print_exc()
                continue

            if state == MSG:
                _safe_call_method(self.coordinator, 'on_worker_msg', worker_id, data)
                continue

            # process job outcome
            job = None
            if state in (RESULT, FAILED, ERROR):
                current_jobs = self.current_jobs[worker_id]
                if current_jobs:
                    job = current_jobs.pop(0)
                else:
                    print(LIB_NAME + 'Coordinator error: getting result without a pending job, worker_id: {}, state: {}'.format(worker_id, state))
                    self._stop_worker(worker_id)
            if state == RESULT:
                _safe_call_method(self.coordinator, 'on_result', worker_id, job, data)
            if state in (FAILED, ERROR):
                _safe_call_method(self.coordinator, 'on_failed', worker_id, job, data)

            if state in (TERMINATED, CRASH, INIT_FAILED):
                _safe_call_method(self.coordinator, 'on_worker_stopped', worker_id)
                self._join_worker(worker_id)

            # dispatch next job or stop worker
            worker = self.workers[worker_id]
            if worker and not worker.stopping:
                status, job, error = _safe_call_method(self.coordinator, 'on_worker_ready', worker_id)
                if status is None:
                    print(LIB_NAME + 'Coordinator error: missing required callback on_worker_ready')
                    self._stop_worker(worker_id)
                elif status is False:
                    print(LIB_NAME + 'Coordinator error: on_worker_ready failed for worker_id: {}, Exception: {}'.format(worker_id, error))
                    traceback.print_exc()
                    self._stop_worker(worker_id)
                elif job is not None:
                    if not self._assign_job(worker_id, job):
                        print(LIB_NAME + 'Coordinator error: failed to assign job to worker_id: {}'.format(worker_id))
                        self._stop_worker(worker_id)
                elif self.context.auto_stop_worker:
                    self._stop_worker(worker_id)

            status, msg, error = _safe_call_method(self.coordinator, 'update_status')
            if status and msg:
                current_len = len(msg)
                if current_len < status_len:
                    msg = msg.ljust(status_len)
                status_len = current_len
                print(msg, end='\r')

        status, msg, error = _safe_call_method(self.coordinator, 'update_status')
        if status and msg:
            print(msg)
        status, result, error = _safe_call_method(self.coordinator, 'cleanup')
        if status is True:
            return result
        return None


def split_list(a, n):
    if n < 1:
        n = 1
    k, m = divmod(len(a), n)
    return [a[i*k + min(i, m):(i + 1)*k + min(i + 1, m)] for i in range(n)]


def rebalance(splits, slot):
    if len(splits[slot]) != 0:
        return

    idx = None
    maxlen = 0
    for i, jobs in enumerate(splits):
        if len(jobs) > maxlen:
            maxlen = len(jobs)
            idx = i
    if idx is not None and maxlen > 1:
        jobs = splits[idx]
        mid = (len(jobs) + 1) // 2
        splits[idx] = jobs[mid:]
        splits[slot] = jobs[:mid]
        splits[slot].reverse()


class RebalanceCoordinator:
    def __init__(self, status_text='job: {done}/{total} worker: {active}/{n}'):
        self.status_text = status_text

    def update_status(self):
        return self.status_text.format(**self.status)

    def init(self, context, tasks):
        self.context = context
        self.tasks = list(tasks)
        n = self.context.coordinator.n
        total = len(self.tasks)
        self.splits = split_list(list(enumerate(self.tasks)), n)
        self.status = {
            'done': 0,
            'failed': 0,
            'total': total,
            'active': n,
            'n': n
        }
        self.last = [None] * n
        self.result = [None] * total
        return True

    def on_worker_ready(self, worker_id):
        if len(self.splits[worker_id]) == 0:
            rebalance(self.splits, worker_id)
        if len(self.splits[worker_id]) == 0:
            self.status['active'] -= 1
            return None
        idx, task = self.splits[worker_id].pop()
        self.last[worker_id] = idx
        return task

    def on_result(self, worker_id, job, result):
        idx = self.last[worker_id]
        if idx is not None:
            self.result[idx] = result
        self.status['done'] += 1

    def on_failed(self, worker_id, job, error):
        idx = self.last[worker_id]
        if idx is not None:
            self.result[idx] = error
        self.status['failed'] += 1

    def cleanup(self):
        return self.result

class DefaultCoordinator:
    def __init__(self, status=False):
        if status:
            self.status = status if isinstance(status, str) else 'job: {done}/{total} worker: {active}/{n}'
        else:
            self.status = None

    def init(self, context, tasks):
        self.tasks = list(tasks)
        self.n = context.coordinator.n
        self.active = context.coordinator.n
        self.total = len(self.tasks)
        self.current = 0
        self.done = 0
        self.working_index = [None] * self.n
        self.results = [None] * self.total

    def update_status(self):
        if self.status:
            return self.status.format(done=self.done, total=self.total, active=self.active, n=self.n)
        return None

    def on_result(self, worker_id, job, result):
        idx = self.working_index[worker_id]
        self.results[idx] = result
        self.done += 1

    def on_worker_ready(self, worker_id):
        if self.current < self.total:
            idx = self.current
            self.working_index[worker_id] = idx
            self.current += 1
            return self.tasks[idx]
        self.active -= 1
        return None

    def cleanup(self):
        return self.results

class Task:
    def __init__(self, worker, coordinator=None, profile_path=''):
        self.worker = worker
        self.coordinator = coordinator
        if coordinator in [None, True, False]:
            self.coordinator = DefaultCoordinator(coordinator)
        self.profile_path = profile_path
        if profile_path == True:
            self.profile_path = tempfile.mkdtemp(prefix='pzmap2dzi_profile_')
        self._process = None

    def post_process(self):
        if self.profile_path:
            stats = pstats.Stats(os.path.join(self.profile_path, 'total.prof'))
            stats.strip_dirs().sort_stats('cumulative').print_stats(20)

    def run(self, tasks, num_workers=None):
        if num_workers is None:
            num_workers = os.cpu_count()
        if num_workers < 1:
            num_workers = 1
        process = _CoordinatorProcess(self.coordinator, self.worker, num_workers, self.profile_path)
        result = process.run(tasks, is_async=False)
        self.post_process()
        return result

    def start(self, tasks, num_workers=None):
        if num_workers is None:
            num_workers = os.cpu_count()
        if num_workers < 1:
            num_workers = 1
        process = _CoordinatorProcess(self.coordinator, self.worker, num_workers, self.profile_path)
        self._process = process
        process.start(tasks)

    def wait(self):
        if self._process:
            result = self._process.wait()
            self.post_process()
            return result
        return None

def _test_worker_func(x):
    if x == 5:
        raise JobFailedException('Job failed for input: {}'.format(x))
    return x * 10

def test():
    tasks = list(range(10))
    task = Task(_test_worker_func, True, True)
    results = task.run(tasks, num_workers=4)
    print('Results:', results)

if __name__ == '__main__':
    test()