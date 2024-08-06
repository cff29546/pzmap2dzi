from multiprocessing import shared_memory
from PIL import Image

def _buffered_image(shm, width, height, extra_size):
    im = Image.frombuffer('RGBA', (width, height), shm.buf[extra_size:],
                          'raw', 'RGBA', 0, 1)
    im.readonly = 0
    return im

class ImageSharedMemory(object):
    def __init__(self, prefix, extra_size=0):
        self.prefix = prefix
        self.created = {}
        self.extra_size = extra_size
        self.loaded = {}

    def create(self, index, width, height):
        size = 4 * width * height + self.extra_size
        try:
            shm = shared_memory.SharedMemory(name=self.prefix+index, create=True, size=size)
        except:
            return None

        self.created[index]=shm
        return _buffered_image(shm, width, height, self.extra_size)

    def load(self, index, width=0, height=0, size_func=None):
        shm = None
        if index in self.created:
            shm = self.created[index]
        if index in self.loaded:
            shm = self.loaded[index]
        if shm is None:
            try:
                shm = shared_memory.SharedMemory(name=self.prefix+index)
            except:
                return None
            self.loaded[index]=shm
        if width * height == 0 and size_func:
            width, height = size_func(shm)
        return _buffered_image(shm, width, height, self.extra_size)

    def get_extra(self, index):
        if index in self.created:
            return self.created[index].buf[0:self.extra_size]
        if index in self.loaded:
            return self.loaded[index].buf[0:self.extra_size]

    def release(self, index):
        if index in self.loaded:
            self.loaded[index].close()
            del self.loaded[index]
        if index in self.created:
            self.created[index].close()
            self.created[index].unlink()
            del self.created[index]

    def __len__(self):
        return len(self.created)

    def clear(self):
        keys = set()
        keys.update(self.loaded)
        keys.update(self.created)
        for key in keys:
            self.release(key)

    def __del__(self):
        self.clear()

def test():
    import random, os
    from PIL import ImageDraw
    import sys
    cmd = 'line'
    if len(sys.argv) > 1:
       cmd = sys.argv[1]
    c = ImageSharedMemory('test')
    im = c.load('a', 128, 128)
    if im:
        if cmd == 'line':
            draw = ImageDraw.Draw(im)
            draw.line((0, random.randint(0,127), 127, random.randint(0,127)), fill=(255,0,0,255))
            draw = None
        if cmd == 't':
            r = im.resize((64,64), Image.LANCZOS)
            im.paste(r, (0,0))
        im.show()
    else:
        print('create shared image')
        im = c.create('a', 128, 128)
        print(len(c))
        os.system('pause')
    im = None
    c.release('a')

if __name__ == '__main__':
    test()
