from __future__ import print_function
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import io
import os
import struct
import time
if __package__ is not None:
    from . import util, mptask, plants

try:
    from . import mem_image
except:
    mem_image = None

def get_version(data):
    if data[:4] == b'PZPK':
        return util.read_uint32(data, 4)[0], 8
    else:
        return 0, 0

def read_texture(data, pos):
    texture = {}
    name, pos = util.read_bytes_with_length(data, pos)
    texture['name'] = name.decode('utf8')
    texture['x'], pos = util.read_int32(data, pos)
    texture['y'], pos = util.read_int32(data, pos)
    texture['w'], pos = util.read_int32(data, pos)
    texture['h'], pos = util.read_int32(data, pos)
    texture['ox'], pos = util.read_int32(data, pos)
    texture['oy'], pos = util.read_int32(data, pos)
    texture['ow'], pos = util.read_int32(data, pos)
    texture['oh'], pos = util.read_int32(data, pos)
    return texture, pos

def read_page(data, pos, version):
    page = {}
    page['name'], pos = util.read_bytes_with_length(data, pos)
    count, pos = util.read_uint32(data, pos)
    page['has_alpha'], pos = util.read_uint32(data, pos)
    textures = []
    for i in range(count):
        texture, pos = read_texture(data, pos)
        textures.append(texture)
    page['textures'] = textures
    if version == 0:
        page['png'], pos = util.read_until(data, pos, b'\xef\xbe\xad\xde') # 0xdeadbeef little endian
    elif version == 1:
        page['png'], pos = util.read_bytes_with_length(data, pos)
    else:
        print('Unsupported pack version {}'.format(version))

    return page, pos

def load_pack(path):
    data = b''
    with open(path, 'rb') as f:
        data = f.read()
    version, pos = get_version(data)
    page_num, pos = util.read_uint32(data, pos)
    print('{}: version {}, {} pages'.format(path, version, page_num))
    pages = []
    for i in range(page_num):
        page, pos = read_page(data, pos, version)
        pages.append(page)
    return pages

def color_sum(pixels):
    total = len(pixels)
    if total > 0:
        r, g, b, _ = map(sum, zip(*pixels))
        return r, g, b, total
    return 0

class Texture(object):
    def __init__(self, im, offset=None):
        if offset:
            ox, oy, ow, oh = offset
            ox = ox - (ow // 2)
            oy = oy - oh # + (pzdzi.SQR_HEIGHT // 2)
        else:
            ox = int(im.info.get('ox', 0))
            oy = int(im.info.get('oy', 0))
        bbox = im.getbbox()
        if bbox and bbox != (0, 0) + im.size:
            self.im = im.crop(bbox)
            self.ox = bbox[0] + ox
            self.oy = bbox[1] + oy
        else:
            self.im = im
            self.ox = ox
            self.oy = oy
        self.color_sum = None

    def render(self, target, x, y):
        w, h = self.im.size
        x = x + self.ox
        y = y + self.oy
        base = target.crop((x, y, x + w, y + h))
        result = Image.alpha_composite(base, self.im)
        target.paste(result, (x, y))

    def get_color_sum(self):
        if self.color_sum is None:
            pixels = list(filter(lambda x: x[3]==255, self.im.getdata()))
            self.color_sum = color_sum(pixels)
        return self.color_sum

    def save(self, path):
        metadata = PngInfo()
        metadata.add_text("ox", str(self.ox))
        metadata.add_text("oy", str(self.oy))
        self.im.save(path, pnginfo=metadata)



class TextureLibrary(object):
    @staticmethod
    def get_size(shm):
        while shm.buf[0] != 1:
            #time.sleep(0.1)
            pass

        w, h = struct.unpack('ii', shm.buf[4:12])
        return w, h


    def __init__(self, texture_path=None, use_cache=False):
        self.texture_path = texture_path
        self.use_cache = use_cache
        self.mem = None
        if use_cache and mem_image:
            self.mem = mem_image.Memory('tl.{}.'.format(os.getpid()), 32)
        self.lib = {}

    def add_pack(self, path, debug=False):
        pages = load_pack(path)
        total = len(pages)
        for idx, page in enumerate(pages):
            print('Processing pages: {}/{}'.format(idx + 1, total), end='\r')
            im = Image.open(io.BytesIO(page['png']))
            for t in page['textures']:
                name = t['name']
                x, y, w, h = t['x'], t['y'], t['w'], t['h']
                ox, oy, ow, oh = t['ox'], t['oy'], t['ow'], t['oh']
                texture = Texture(im.crop((x, y, x + w, y + h)), (ox, oy, ow, oh))
                if debug and self.lib.get(name, None):
                    print('Conflict texture: {}'.format(name))
                self.lib[name] = texture

    def add_from_pz_path(self, pzmain, debug=False):
        files = [
            'Erosion.pack',
            'ApCom.pack',
            'RadioIcons.pack',
            'ApComUI.pack',
            'JumboTrees2x.pack',
            'Tiles2x.floor.pack',
            'Tiles2x.pack',
        ]
        for f in files:
            self.add_pack(os.path.join(pzmain, 'media', 'texturepacks', f), debug)
    
    def set_texture_path(self, path):
        self.texture_path = path

    def load_texture(self, name):
        t = None
        if self.mem is not None:
            im = self.mem.load(name, size_func=TextureLibrary.get_size)
            if im:
                extra = self.mem.get_extra(name)
                ox, oy = struct.unpack('ii', extra[12:20])
                t = Texture(im, (ox, oy, 0, 0))

        if t is None and self.texture_path:
            file_path = os.path.join(self.texture_path, name + '.png')
            if os.path.exists(file_path):
                im = Image.open(file_path)
                if im:
                    t = Texture(im)
                    if self.mem is not None:
                        cached_im = self.mem.create(name, *t.im.size)
                        if cached_im:
                            cached_im.paste(t.im, (0, 0))
                            extra = self.mem.get_extra(name)
                            info = t.im.size + (t.ox, t.oy)
                            extra[4:20] = struct.pack('iiii', *info)
                            extra[0] = 1
                        return self.load_texture(name)

        if t is None:
            print('missing texture [{}]'.format(name))
        self.lib[name] = t
        return t

    def get_by_name(self, name):
        if name in self.lib:
            return self.lib[name]

        return self.load_texture(name)

    def save_all(self, path, parallel=1):
        if not util.ensure_folder(path):
            return False
        t = mptask.Task(SaveImg(path), mptask.SplitScheduler(True))
        t.run(list(self.lib.items()), parallel)

    def blend_textures(self, names):
        w, h = 384, 512
        im = Image.new('RGBA', (w, h))
        x = w // 2
        y = h # - (pzdzi.SQR_HEIGHT // 2)
        for name in names:
            t = self.get_by_name(name)
            if t:
                t.render(im, x, y)
        return Texture(im, (0, 0, w, h))

    def config_plants(self, season='spring', snow=False, flower=False, large_bush=False,
                 tree_size=1, jumbo_size=3, jumbo_type=3):
        pi = plants.PlantsInfo(season, snow, flower, large_bush, tree_size, jumbo_size, jumbo_type)
        for key, names in pi.mapping.items():
            self.lib[key] = self.blend_textures(names)

    def __del__(self):
        if self.mem is not None:
            self.lib = {}
            self.mem.clear()

class SaveImg(object):
    def __init__(self, path):
        self.path = path

    def on_job(self, job):
        name, im = job
        im.save(os.path.join(self.path, name + '.png'))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ texture unpacker')
    parser.add_argument('-o', '--output', type=str, default='.')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--test-plants', action='store_true')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('-z', '--pz-path', type=str, default='')
    parser.add_argument('packs', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    
    lib = TextureLibrary()
    if args.pz_path:
        lib.add_from_pz_path(args.pz_path, args.debug)
    for pack_path in args.packs:
        lib.add_pack(pack_path, args.debug)
    if args.test_plants:
        lib.config_plants('summer2', True, True, True, 3, 5)
    lib.save_all(args.output, args.mp)
    #lib.save_pages(args.output)
    
