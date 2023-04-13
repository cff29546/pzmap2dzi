from multiprocessing import shared_memory
from PIL import Image

def _buffer_image(shm, width, height):
    im = Image.frombuffer('RGBA', (width, height), shm.buf, 'raw', 'RGBA', 0, 1)
    im.readonly = 0
    return im

class Memory(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.created = {}
        self.loaded = {}

    def create(self, index, width, height):
        size = 4 * width * height
        try:
            shm = shared_memory.SharedMemory(name=self.prefix+index, create=True, size=size)
        except:
            return None

        self.created[index]=shm
        return _buffer_image(shm, width, height)

    def load(self, index, width, height):
        if index in self.created:
            return _buffer_image(self.created[index], width, height)
        if index in self.loaded:
            return _buffer_image(self.loaded[index], width, height)
        size = 4 * width * height
        try:
            shm = shared_memory.SharedMemory(name=self.prefix+index, size=size)
        except:
            return None

        self.loaded[index]=shm
        return _buffer_image(shm, width, height)

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

def test():
    import random, os
    from PIL import ImageDraw
    import sys
    cmd = 'line'
    if len(sys.argv) > 1:
       cmd = sys.argv[1]
    c = Memory('test')
    im = c.load('a', 128, 128)
    if im:
        if cmd == 'line':
            draw = ImageDraw.Draw(im)
            draw.line((0, random.randint(0,127), 127, random.randint(0,127)), fill=(255,0,0,255))
            draw = None
        if cmd == 't':
            r = im.resize((64,64), Image.ANTIALIAS)
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
