import pynput
try:
    import queue
except:
    import Queue as queue

def is_hotkey(k):
    try:
        if pynput.keyboard.HotKey.parse(k):
            return True
    except ValueError:
        return False
    return False

class _hotkey(object):
    """
    hotkey format:
        <ctrl>+<alt>+a    ctrl + alt + a
        a                 the key "a"
        <f8>              f8
        <cmd>+<f2>        windows + f2
    """
    def __init__(self, hotkeys=[]):
        self.q = None
        self.gh = None
        hotkeys = list(filter(is_hotkey, hotkeys))
        self.hotkey_map = {hotkey: self._make_func(hotkey) 
                           for hotkey in hotkeys}
        self._start()

    def _start(self):
        self.stop()
        self.q = queue.Queue()
        self.gh = pynput.keyboard.GlobalHotKeys(self.hotkey_map)
        self.gh.start()
        self.gh.wait()

    def stop(self):
        if self.gh:
            self.gh.stop()
            self.gh.join()
            self.gh = None
        if self.q:
            while self.peek():
                pass
            self.q.join()
            self.q = None

    def _make_func(self, hotkey):
        return lambda : self._on_hotkey(hotkey)
    def _on_hotkey(self, hotkey):
        self.q.put(hotkey)

    def wait(self):
        if self.q:
            key = self.q.get()
            self.q.task_done()
            return key
        raise Exception('Listener not start.')

    def peek(self):
        if self.q:
            try:
                key = self.q.get(block=False)
                self.q.task_done()
            except queue.Empty:
                key = None
            return key
        else:
            raise Exception('Listener not start.')

    def __del__(self):
        self.stop() 

def wait_any(hotkeys=['<f{}>'.format(i) for i in range(1, 13)]):
    h = _hotkey(hotkeys)
    key = h.wait()
    h.stop()
    return key

def listener(hotkeys=['<f{}>'.format(i) for i in range(1, 13)]):
    return _hotkey(hotkeys)

