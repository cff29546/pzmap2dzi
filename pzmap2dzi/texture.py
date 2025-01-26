from __future__ import print_function
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import PIL
import io
import os
import struct
import time
import yaml
if __package__ is not None:
    from . import util, mptask, plants

try:
    from . import shared_memory_image
except:
    shared_memory_image = None


def get_version(data):
    if data[:4] == b'PZPK':
        return util.read_uint32(data, 4)
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
        # magic 0xdeadbeef little endian
        page['png'], pos = util.read_until(data, pos, b'\xef\xbe\xad\xde')
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
    return 0, 0, 0, 1


class Texture(object):
    def __init__(self, im, offset=None):
        if offset:
            ox, oy = offset
        else:
            ox = int(im.info.get('ox', 0))
            oy = int(im.info.get('oy', 0))
        bbox = im.getbbox()
        if bbox is None:
            self.im = Image.new('RGBA', (0, 0))
            self.ox = 0
            self.oy = 0
        elif bbox != (0, 0) + im.size:
            self.im = im.crop(bbox)
            self.ox = bbox[0] + ox
            self.oy = bbox[1] + oy
        else:
            self.im = im
            self.ox = ox
            self.oy = oy
        self.color_sum = None

    if tuple(map(int, PIL.__version__.split('.'))) >= (10, 4, 0):
        def render(self, target, x, y):
            x = x + self.ox
            y = y + self.oy
            target.alpha_composite(self.im, (x, y))
    else:
        def render(self, target, x, y):
            w, h = self.im.size
            x = x + self.ox
            y = y + self.oy
            base = target.crop((x, y, x + w, y + h))
            result = Image.alpha_composite(base, self.im)
            target.paste(result, (x, y))

    def get_color_sum(self):
        if self.color_sum is None:
            pixels = list(filter(lambda x: x[3] == 255, self.im.getdata()))
            self.color_sum = color_sum(pixels)
        return self.color_sum

    def save(self, path):
        metadata = PngInfo()
        metadata.add_text('ox', str(self.ox))
        metadata.add_text('oy', str(self.oy))
        self.im.save(path, pnginfo=metadata)


class TextureLibrary(object):
    @staticmethod
    def get_size(shm):
        while shm.buf[0] != 1:
            # spin lock wait
            # time.sleep(0.1)
            pass

        w, h = struct.unpack('ii', shm.buf[4:12])
        return w, h

    def __init__(self, texture_path=[], cache_name='',
                 page_mode=False, page_size=1024):
        self.texture_path = texture_path
        self.use_cache = True if cache_name else False
        self.page_mode = page_mode
        self.page_size = page_size
        self.page = []
        self.page_buffer = None
        self.mapping = {}
        self.mem = None
        if self.use_cache and shared_memory_image:
            prefix = 'tl.{}.{}'.format(os.getpid(), cache_name)
            self.mem = shared_memory_image.ImageSharedMemory(prefix, 32)
        self.lib = {}

    def add_pack(self, path, debug=False):
        if not os.path.isfile(path):
            return
        pages = load_pack(path)
        total = len(pages)
        for idx, page in enumerate(pages):
            print('Processing pages: {}/{}'.format(idx + 1, total), end='\r')
            im = Image.open(io.BytesIO(page['png']))
            if self.page_mode:
                page_id = len(self.page)
                self.page.append(im)
            for t in page['textures']:
                name = t['name']
                x, y, w, h = t['x'], t['y'], t['w'], t['h']
                ox, oy, ow, oh = t['ox'], t['oy'], t['ow'], t['oh']
                ox -= ow >> 1
                oy -= oh
                texture = Texture(im.crop((x, y, x + w, y + h)), (ox, oy))
                if debug and self.lib.get(name, None):
                    print('Conflict texture: {}'.format(name))
                self.lib[name] = texture
                if self.page_mode:
                    self.mapping[name] = page_id, x, y, w, h, ox, oy

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
        packs = os.path.join(pzmain, 'media', 'texturepacks')
        for f in files:
            self.add_pack(os.path.join(packs, f), debug)

    def set_texture_path(self, path):
        self.texture_path = path

    def load_raw_texture(self, name):
        for path in self.texture_path:
            file_path = os.path.join(path, name + '.png')
            if os.path.exists(file_path):
                im = Image.open(file_path)
                if im:
                    return Texture(im)

    def load_from_cache(self, name):
        t = None
        if self.mem is not None:
            im = self.mem.load(name, size_func=TextureLibrary.get_size)
            if im:
                extra = self.mem.get_extra(name)
                ox, oy = struct.unpack('ii', extra[12:20])
                t = Texture(im, (ox, oy))
        return t

    def save_to_cache(self, name, t):
        if self.mem is not None:
            cached_im = self.mem.create(name, *t.im.size)
            if cached_im:
                cached_im.paste(t.im, (0, 0))
                extra = self.mem.get_extra(name)
                info = t.im.size + (t.ox, t.oy)
                extra[4:20] = struct.pack('iiii', *info)
                extra[0] = 1

            # free current and reload using shared memory
            cached = self.load_from_cache(name)
            if cached:
                return cached
        return t

    def load_pages(self):
        if self.texture_path:
            page_ids = []
            pattern = re.compile('(\\d+)\\.png')
            for f in os.listdir(self.texture_path):
                m = pattern.match(f)
                if m:
                    page_ids.append(int(m.groups()[0]))
            path = os.path.join(self.texture_path, 'mapping.yaml')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.mapping = yaml.safe_load(f.read())
            page_count = max(page_ids) + 1
            w, h = self.page_size, self.page_size
            self.page_buffer = memoryview(bytes(4 * w * h * page_count))
            for pid in page_ids:
                path = os.path.join(self.texture_path, '{}.png'.format(pid))
                if os.path.exists(path):
                    im = Image.open(path)
                    if im:
                        offset = 4 * w * h * pid
                        buf_im = Image.frombuffer('RGBA', (w, h),
                                                  self.page_buffer[offset:],
                                                  'raw', 'RGBA', 0, 1)
                        buf_im.readonly = 0
                        buf_im.paste(im, (0, 0))

    def load_texture(self, name):
        t = self.load_from_cache(name)

        if t is None:
            t = self.load_raw_texture(name)
            if t is not None:
                t = self.save_to_cache(name, t)

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
        if self.page_mode:
            tasks = list(enumerate(self.page))
            with open(os.path.join(path, 'mapping.yaml'), 'w') as f:
                f.write(yaml.safe_dump(self.mapping))
        else:
            tasks = list(self.lib.items())
        t.run(tasks, parallel)

    def blend_textures(self, names):
        w, h = 384, 512
        im = Image.new('RGBA', (w, h))
        x = w >> 1
        y = h  # - (pzdzi.SQR_HEIGHT // 2)
        for name in names:
            t = self.get_by_name(name)
            if t:
                t.render(im, x, y)
        return Texture(im, (-x, -y))

    def config_plants(self, conf):
        pi = plants.PlantsInfo(conf)
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
        im.save(os.path.join(self.path, '{}.png'.format(name)))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ texture unpacker')
    parser.add_argument('-o', '--output', type=str, default='.')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--test-plants', action='store_true')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('-z', '--pz-path', type=str, default='')
    parser.add_argument('-p', '--page-mode', action='store_true')
    parser.add_argument('packs', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    lib = TextureLibrary(page_mode=args.page_mode)
    if args.pz_path:
        lib.add_from_pz_path(args.pz_path, args.debug)
    for pack_path in args.packs:
        lib.add_pack(pack_path, args.debug)
    if args.test_plants:
        lib.config_plants({
            'snow': True,
            'flower': True,
            'large_bush': True,
            'tree_size': 3,
            'jumbo_tree_size': 5,
        })
    lib.save_all(args.output, args.mp)
    # lib.save_pages(args.output)
