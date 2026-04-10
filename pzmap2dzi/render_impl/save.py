from . import base
from ..plants import jumbo_tree_defs
import os
import re
import sys
import requests
import zipfile
import importlib
import struct

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

OLD_BLOCK_NAME = re.compile(r'^map_(\d+)_(\d+)\.bin$')
NEW_BLOCK_NAME = re.compile(r'^(\d+)\.bin$')
def scan_blocks(save_game_path, first_only=False):
    blocks = {}
    path_type = 'map/map_{}_{}.bin'
    map_dir = os.path.join(save_game_path, 'map')
    if os.path.isdir(map_dir):
        # new format
        for folder in os.listdir(map_dir):
            if not os.path.isdir(os.path.join(map_dir, folder)):
                continue
            if not folder.isdigit():
                continue
            x = int(folder)
            for name in os.listdir(os.path.join(map_dir, folder)):
                m = NEW_BLOCK_NAME.match(name)
                if m:
                    y = int(m.group(1))
                    blocks[(x, y)] = os.path.normpath(os.path.join(map_dir, folder, name))
                    path_type = 'map/{}/{}.bin'
                    if first_only:
                        return blocks, path_type
    else:
        map_dir = save_game_path
        path_type = 'map_{}_{}.bin'
    for name in os.listdir(map_dir):
        m = OLD_BLOCK_NAME.match(name)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            blocks[(x, y)] = os.path.normpath(os.path.join(map_dir, name))
            if first_only:
                return blocks, path_type
    return blocks, path_type


def get_save_version(save_game_path):
    blocks, path_type = scan_blocks(save_game_path, first_only=True)
    if not blocks:
        return None, None
    block_path = blocks.popitem()[1]
    with open(block_path, 'rb') as f:
        data = f.read(5)
        if len(data) < 5:
            return None, None
    version = struct.unpack('>I', data[1:5])[0]
    path_template = os.path.normpath(os.path.join(save_game_path, path_type))
    return version, path_template


def match_version(map_version, world_version):
    if world_version is None:
        return False
    save_version = 'B41' if world_version <= 195 else 'B42'
    return map_version == save_version

class LibLoader(object):
    def __init__(self, lib_path, api_base=None):
        self.lib_path = lib_path
        self.api_base = 'https://api.github.com/repos/cff29546/pzdataspec/releases/'
        if api_base:
            self.api_base = api_base
    
    def download_artifact(self, url, file_name):
        r = requests.get(url)
        if r.status_code != 200:
            return False
        path = os.path.join(self.lib_path, file_name)
        with open(path, 'wb') as f:
            f.write(r.content)
        return True

    def load(self, module_name):
        update_path = False
        if self.lib_path not in sys.path:
            sys.path.append(self.lib_path)
            update_path = True
        module = None
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            print('Failed to import module {}: {}'.format(module_name, e))
            module = None
        if update_path:
            sys.path.remove(self.lib_path)
        return module

    def expand_artifact(self, file_name):
        path = os.path.join(self.lib_path, file_name)
        if not os.path.exists(path):
            return False
        with zipfile.ZipFile(path) as z:
            z.extractall(self.lib_path)
        return True

    def install(self, tag):
        if not os.path.isdir(self.lib_path):
            if os.path.exists(self.lib_path):
                return None
            os.makedirs(self.lib_path)
        zip_name = 'pzdataspec-{}.zip'.format(tag)
        if self.expand_artifact(zip_name):
            return True

        if tag == 'latest':
            api_url = self.api_base + 'latest'
        else:
            api_url = self.api_base + 'tags/' + tag
        print('installing parser from {}'.format(api_url))
        r = requests.get(api_url)
        if r.status_code != 200:
            return None
        data = r.json()
        if tag == 'latest':
            tag = data['tag_name']
            zip_name = 'pzdataspec-{}.zip'.format(tag)
            if self.expand_artifact(zip_name):
                return True
        
        zip_url = None
        for asset in data.get('assets', []):
            if asset['name'].endswith('.zip'):
                zip_url = asset['browser_download_url']
                break
        if not zip_url:
            return None
        print('downloading parser from {}'.format(zip_url))
        self.download_artifact(zip_url, zip_name)
        if self.expand_artifact(zip_name):
            return True
        return None

class SaveGameBase(base.TextureRender):
    OLD_BLOCK_NAME = re.compile(r'map_(\d+)_(\d+).bin')
    NEW_BLOCK_NAME = re.compile(r'(\d+).bin')
    def __init__(self, **options):
        options.setdefault('plants_conf', {}).setdefault('jumbo_tree_size', 4)
        self.use_jumbo_tree = options['plants_conf']['jumbo_tree_size'] > 3
        base.TextureRender.__init__(self, **options)
        self.pz_root = options.get('pz_root')
        self.mod_root = options.get('mod_root')
        save_root = os.path.expandvars(options.get('save_game_root'))
        save_game = options.get('save_game') # save game folder name
        self.save_game = os.path.normpath(os.path.join(save_root, save_game))
        self.output = options.get('output')
        self.parser = None
        self.parser_tag = options.get('save_game_parser_tag', 'latest')
        parser_path = os.path.normpath(os.path.join(options['output_root'], 'lib'))
        if self.parser_tag == 'local' and options.get('save_game_parser_path'):
            parser_path = options['save_game_parser_path']
        self.lib_loader = LibLoader(parser_path)
        self.init_in_worker = False

    def update_options(self, options):
        options['render_margin'] = 'large' if self.use_jumbo_tree else 'normal'
        options['source_tags'] = ['save']
        options['source_path'] = 'save_game'
        options['source_unit_size'] = 'block'
        return options

    def load_block(self, x, y):
        block_path = self.path_template.format(x, y)
        if not os.path.exists(block_path):
            return None
        return self.utils.load_chunk(block_path, self.save_version)

    def init_dzi(self, dzi):
        version, path_template = get_save_version(self.save_game)
        if not version:
            self.NO_IMAGE = True
            return
        self.path_template = path_template
        lib_tag = self.parser_tag
        self.block_size = 8
        self.save_version = 42
        if version <= 195:
            self.block_size = 10
            self.save_version = 41
        if lib_tag == 'local':
            print('Using local parser from {}'.format(os.path.abspath(self.lib_loader.lib_path)))
        else:
            self.lib_loader.install(lib_tag)
        utils = self.lib_loader.load('pzdataspec.utils')
        if not utils:
            print('Failed to load parser utils')
            self.NO_IMAGE = True
            return
        if self.block_size != dzi.block_size:
            print('Block size mismatch, map:{}, save:{}, skip rendering'.format(dzi.block_size, self.block_size))
            self.NO_IMAGE = True
            return
        return

    def init_worker(self, dzi):
        self.utils = self.lib_loader.load('pzdataspec.utils')
        self.tiledef = self.utils.load_tile_defs(self.pz_root, self.mod_root, self.save_version)
        jumbo_tree_file_number = 5 if self.save_version == 41 else 6
        self.tiledef.update(jumbo_tree_defs(jumbo_tree_file_number))
        world_dict_path = os.path.normpath(os.path.join(self.save_game, 'WorldDictionary.bin'))
        world_dict_sprites = self.utils.load_world_dict_sprites(world_dict_path, self.save_version)
        self.tiledef.update(world_dict_sprites)
        self.load_block_cached = lru_cache(maxsize=128)(self.load_block)
        self.init_in_worker = True


class SaveGameRender(SaveGameBase):
    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        oy += dzi.sqr_height >> 1  # center -> bottom center
        if not self.init_in_worker:
            self.init_worker(dzi)
        wx, x = divmod(sx, self.block_size)
        wy, y = divmod(sy, self.block_size)
        block = self.load_block_cached(wx, wy)
        if not block:
            return
        sprites = block.get_sprites(layer, x, y)
        if not sprites:
            return
        for s in sprites:
            tile_name = self.tiledef.get(s)
            if not tile_name:
                print('missing tiledef for sprite: {}'.format(s))
                continue
            tex = self.tl.get_by_name(tile_name)
            if tex:
                tex.render(im_getter.get(), ox, oy)
            else:
                print('missing tile: {}'.format(s))


class SaveGameTopRender(SaveGameBase):
    def __init__(self, **options):
        super().__init__(**options)
        mode = options.get('top_view_color_mode', 'base+water')
        self.color = base.BaseTopRender.COLOR_FUNC[mode]

    def square(self, im_getter, dzi, ox, oy, sx, sy, layer):
        if not self.init_in_worker:
            self.init_worker(dzi)
        wx, x = divmod(sx, self.block_size)
        wy, y = divmod(sy, self.block_size)
        block = self.load_block_cached(wx, wy)
        if not block:
            return
        sprites = block.get_sprites(layer, x, y)
        if not sprites:
            return
        tiles = filter(None, map(self.tiledef.get, sprites))
        color = self.color(self.tl, tiles, layer)
        if color is None:
            return
        draw = im_getter.get_draw()
        box_size = dzi.square_size - 1
        box = [ox, oy, ox + box_size, oy + box_size]
        draw.rectangle(box, fill=color)

    def block(self, im_getter, dzi, ox, oy, wx, wy, layer):
        block = self.load_block(wx, wy)
        if not block:
            return
        draw = None
        size = dzi.square_size
        box_size = size - 1
        for x in range(dzi.block_size):
            for y in range(dzi.block_size):
                sprites = block.get_sprites(layer, x, y)
                if not sprites:
                    continue
                tiles = filter(None, map(self.tiledef.get, sprites))
                color = self.color(self.tl, tiles, layer)
                if color is None:
                    continue
                if draw is None:
                    draw = im_getter.get_draw()
                px = ox + x * size
                py = oy + y * size
                box = [px, py, px + box_size, py + box_size]
                draw.rectangle(box, fill=color)
    
    def tile(self, im_getter, dzi, cx, cy, layer):
        if not self.init_in_worker:
            self.init_worker(dzi)

        size = dzi.square_size * dzi.block_size
        count = dzi.cell_size_in_block
        wx0 = cx * count
        wy0 = cy * count
        for wx in range(count):
            ox = wx * size
            for wy in range(count):
                oy = wy * size
                self.block(im_getter, dzi, ox, oy, wx0 + wx, wy0 + wy, layer)