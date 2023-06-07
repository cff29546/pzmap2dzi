import flask
import waitress
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

MAP = re.compile('^map_(\\d+)_(\\d+)\\.bin$')
@app.route('/load/<path:save>')
def load(save):
    path = app.config.get('save_path', None)
    if not os.path.isdir(os.path.join(path, save)):
        return ''
    blocks = []
    if path:
        files = os.listdir(os.path.join(path, save))
        for f in files:
            m = MAP.match(f)
            if m:
                x, y = map(int, m.groups())
                blocks.append('{},{}'.format(x, y))

    return ';'.join(blocks)

@app.route('/delete/<path:save>', methods=['POST'])
def delete_save(save):
    if flask.request.method == 'POST':
        path = app.config.get('save_path', None)
        if not os.path.isdir(os.path.join(path, save)):
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
        
        backup = flask.request.form.get('backup', None)

        if path:
            print('trimming [{}]'.format(save))
            for x, y in block:
                name = os.path.join(path, save, 'map_{}_{}.bin'.format(x, y))
                if os.path.isfile(name):
                    print('delete block {},{}'.format(x, y))
                    os.remove(name)
            for x, y in cell:
                name = os.path.join(path, save, 'chunkdata_{}_{}.bin'.format(x, y))
                if os.path.isfile(name):
                    print('delete cell chunkdata {},{}'.format(x, y))
                    os.remove(name)
                name = os.path.join(path, save, 'zpop_{}_{}.bin'.format(x, y))
                if os.path.isfile(name):
                    print('delete cell zpop {},{}'.format(x, y))
                    os.remove(name)
                for i in range(30):
                    for j in range(30):
                        bx = x * 30 + i
                        by = y * 30 + j
                        name = os.path.join(path, save, 'map_{}_{}.bin'.format(bx, by))
                        if os.path.isfile(name):
                            print('delete block {},{}'.format(bx, by))
                            os.remove(name)

    return 'done'

@app.route('/<path:filename>')
def static_files(filename):
    return flask.send_from_directory('.', filename)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi viewer server')
    parser.add_argument('-c', '--conf', type=str, default=None)
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('save_path', nargs='?', default=None)
    args = parser.parse_args()
    if args.save_path:
        app.config['save_path'] = args.save_path
    else:
        for key, value in load_conf(args.conf).items():
            app.config[key] = value
    if args.debug:
        app.run(host='localhost', port=8880)
    else:
        waitress.serve(app, host='localhost', port=8880)
