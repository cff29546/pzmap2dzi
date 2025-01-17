import flask
import waitress
import sqlite3
import struct
import json
import os
import re

app = flask.Flask(__name__)

def load_conf(config_path=None):
    if config_path is None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(dir_path, 'server_config.txt')
    conf = {}
    with open(config_path, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                conf[key] = value
    if 'save_path' in conf:
        conf['save_path'] = os.path.expandvars(conf['save_path'])
    return conf

@app.route('/browse')
def browse():
    path = app.config.get('save_path', None)
    cmd = 'start "" "{}"'.format(path)
    if os.system(cmd) == 0:
        return ""
    else:
        flask.abort(404);

@app.route('/list_save')
def list_save():
    path = app.config.get('save_path', None)
    saves = []
    if path:
        modes = os.listdir(path)
        for mode in modes:
            for save in os.listdir(os.path.join(path, mode)):
                saves.append(os.path.join(mode, save))

    return json.dumps(saves)


SIGNATURE_MAP = {
    (300, 300, 8): 'B41',
    (256, 256, 32): 'B42',
}
PATH_MAP = {
    'map': {
        'B42': 'map',
        'B41': '.',
    },
    'chunkdata': {
        'B42': 'chunkdata',
        'B41': '.',
    },
    'zpop': {
        'B42': 'zpop',
        'B41': '.',
    },
    'apop': {
        'B42': 'apop',
        'B41': '.',
    },
}

CELL_IN_BLOCK = {
    'B41': 30,
    'B42': 32,
}

def get_version(path):
    map_bin = os.path.join(path, 'map.bin')
    if os.path.exists(map_bin):
        with open(map_bin, 'rb') as f:
            data = f.read()
        if len(data) < 12:
            return 'unknown'
        cx, cy, layer = struct.unpack('>iii', data[:12])
        return SIGNATURE_MAP.get((cx, cy, layer), 'unknown')
    return 'unknown'

MAP = re.compile('^map_(\\d+)_(\\d+)\\.bin$')
@app.route('/load/<path:save>')
def load(save):
    path = app.config.get('save_path', None)
    save_path = os.path.join(path, save)
    if not os.path.isdir(save_path):
        return ''
    blocks = []
    if path:
        version = get_version(save_path)
        files = os.listdir(os.path.join(path, save, PATH_MAP['map'].get(version, '.')))
        for f in files:
            m = MAP.match(f)
            if m:
                x, y = map(int, m.groups())
                blocks.append('{},{}'.format(x, y))
    return {'version': version, 'blocks': ';'.join(blocks)}

def remove_bin(save_path, mode, version, x, y):
    folder = PATH_MAP[mode].get(version, '.')
    name = os.path.join(save_path, folder, '{}_{}_{}.bin'.format(mode, x, y))
    if os.path.isfile(name):
        print('delete {} {},{}'.format(mode, x, y))
        os.remove(name)

@app.route('/delete/<path:save>', methods=['POST'])
def delete_save(save):
    if flask.request.method != 'POST':
        return ''

    path = app.config.get('save_path', None)
    save_path = os.path.join(path, save)
    if not os.path.isdir(save_path):
        return ''

    cell_str = flask.request.form.get('cells', None)
    cell = []
    if cell_str:
        for c in cell_str.split(';'):
            x, y = map(int, c.split(','))
            cell.append((x, y))

    block_str = flask.request.form.get('blocks', None)
    block = []
    if block_str:
        for c in block_str.split(';'):
            x, y = map(int, c.split(','))
            block.append((x, y))
    
    #backup = flask.request.form.get('backup', None)
    print('trimming [{}]'.format(save))
    if app.debug:
        print('req: ', flask.request.form)
    version = get_version(save_path)
    vehicles = None
    cursor = None
    cb = CELL_IN_BLOCK.get(version, 0)
    if flask.request.form.get('vehicles', False):
        db_path = os.path.join(save_path, 'vehicles.db')
        if os.path.isfile(db_path):
            vehicles = sqlite3.connect(db_path)
            cursor = vehicles.cursor()

    for x, y in block:
        remove_bin(save_path, 'map', version, x, y)
        if cursor:
            sql = 'DELETE FROM vehicles WHERE wx = {} AND wy = {};'.format(x, y)
            cursor.execute(sql)

    for x, y in cell:
        types = ['chunkdata', 'zpop']
        if flask.request.form.get('animals', False):
            types.append('apop')

        for t in types:
            remove_bin(save_path, t, version, x, y)

        if cursor:
            sql = 'DELETE FROM vehicles WHERE wx >= {} AND wx < {} AND wy >= {} AND wy < {};'
            sql = sql.format(x * cb, (x + 1) * cb, y * cb, (y + 1) * cb)
            cursor.execute(sql)

        for i in range(cb):
            for j in range(cb):
                bx = x * cb + i
                by = y * cb + j
                remove_bin(save_path, 'map', version, bx, by)

    if vehicles:
        vehicles.commit()
        vehicles.close()

    return 'done'

@app.route('/<path:filename>')
def static_files(filename):
    return flask.send_from_directory('.', filename)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi viewer server')
    parser.add_argument('-c', '--conf', type=str, default=None)
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    for key, value in load_conf(args.conf).items():
        app.config[key] = value
    if args.debug:
        app.debug = True
        app.run(host=app.config['host'], port=8880)
    else:
        waitress.serve(app, host=app.config['host'], port=8880)
