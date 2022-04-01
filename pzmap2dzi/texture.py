from __future__ import print_function
from PIL import Image
import io
import os
if __package__ is not None:
    from . import util, mp, plants

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

class Texture(object):
    def __init__(self, im, ox, oy):
        bbox = im.getbbox()
        if bbox:
            self.im = im.crop(bbox)
            self.ox = bbox[0] + ox
            self.oy = bbox[1] + oy
        else:
            self.im = im
            self.ox = ox
            self.oy = oy

    def render(self, target, x, y):
        #target.paste(self.im, (x + self.ox, y + self.oy), self.im)
        w, h = self.im.size
        x = x + self.ox
        y = y + self.oy
        base = target.crop((x, y, x + w, y + h))
        result = Image.alpha_composite(base, self.im)
        target.paste(result, (x, y))

    def save(self, path):
        w, h = self.im.size
        out_im = Image.new('RGBA', (self.ox + w, self.oy + h))
        self.render(out_im, 0, 0)
        out_im.save(path)


class TextureLibrary(object):
    def __init__(self, texture_path=None):
        self.texture_path = texture_path
        self.lib = {}

    def add_pack(self, path, debug=False):
        pages = load_pack(path)
        total = len(pages)
        done = 0
        for page in pages:
            print('Processing pages: {}/{}'.format(done, total), end='\r')
            done += 1
            im = Image.open(io.BytesIO(page['png']))
            for t in page['textures']:
                name = t['name']
                x, y, w, h = t['x'], t['y'], t['w'], t['h']
                ox, oy = t['ox'], t['oy']
                texture = Texture(im.crop((x, y, x + w, y + h)), ox, oy)
                if debug and self.lib.get(name, None):
                    print('Overwrite t: {}'.format(name))
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

    def get_by_name(self, name):
        t = self.lib.get(name, None)
        if t:
            return t

        if self.texture_path:
            file_path = os.path.join(self.texture_path, name + '.png')
            if os.path.exists(file_path):
                im = Image.open(file_path)
                if im:
                    if 'JUMBO' in name:
                        t = Texture(im, -128, -256)
                    else:
                        t = Texture(im, 0, 0)
                    self.lib[name] = t
                    return t
        return None

    def save_all(self, path, parallel=1):
        if not util.ensure_folder(path):
            return False
        t = mp.Task(save_img, path, parallel)
        t.run(list(self.lib.items()), True)
        '''
        for name, texture in self.lib.items():
            texture.save(os.path.join(path, name + '.png'))
        '''
                
    def blend_textures(self, names, jumbo=False):
        if jumbo:
            im = Image.new('RGBA', (384, 512))
            x, y = 128, 256
        else:
            im = Image.new('RGBA', (128, 256))
            x, y = 0, 0
        for name in names:
            t = self.get_by_name(name)
            if t:
                t.render(im, x, y)
        return Texture(im, -x, -y)

    def config_plants(self, season='spring', snow=False, flower=False, large_bush=False,
                 tree_size=1, jumbo_size=3, jumbo_type=3):
        pi = plants.PlantsInfo(season, snow, flower, large_bush, tree_size, jumbo_size, jumbo_type)
        for key, names in pi.mapping.items():
            self.lib[key] = self.blend_textures(names, key.startswith('jumbo_tree'))

def save_img(path, job):
    name, im = job
    im.save(os.path.join(path, name + '.png'))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ texture unpacker')
    parser.add_argument('-o', '--output', type=str, default='.')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('input', type=str)
    args = parser.parse_args()
    
    lib = TextureLibrary()
    lib.add_from_pz_path(args.input, args.debug)
    lib.save_all(args.output, args.mp)
    
