import json
import yaml
import os
import io


def load_json(path):
    with io.open(path, 'r', encoding='utf8') as f:
        return json.loads(f.read())


def load_yaml(path):
    with io.open(path, 'r', encoding='utf8') as f:
        return yaml.safe_load(f.read())


def save_json(path, data):
    with io.open(path, 'wb') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False).encode('utf8'))


def save_yaml(path, data):
    with io.open(path, 'w', encoding='utf8') as f:
        f.write(yaml.safe_dump(data, encoding=None, allow_unicode=True))


def update_data(data, update):
    for key, value in update.items():
        if isinstance(value, dict):
            data[key] = update_data(data.get(key, {}), value)
        else:
            data[key] = value
    return data


def update_json(path, update):
    data = {}
    if os.path.isfile(path):
        data = load_json(path)
    data = update_data(data, update)
    save_json(path, data)


# marks
def concat_dict(data, splitor):
    kvs = []
    for k, v in data.items():
        kvs.append(k + ':' + v)
    return splitor.join(sorted(kvs))


def recover_dict(data, splitor):
    kvs = data.split(splitor)
    d = {}
    for kv in kvs:
        if ':' in kv:
            k, v = kv.split(':', 1)
        else:
            k = 'en'
            v = kv
        d[k.strip()] = v.strip()
    return d


TEXT_KEYS = ['name', 'desc']
def yaml_item2json_aio(y, splitor='&&'):
    j = {}
    for key in y:
        if key.split('_')[0] in TEXT_KEYS:
            k, v = key.split('_', 1)
            if k not in j:
                j[k] = {}
            j[k][v] = y[key]
        else:
            j[key] = y[key]
    for key in TEXT_KEYS:
        j[key] = concat_dict(j.get(key, {}), splitor)
    return j


def json_aio_item2yaml(j, splitor='&&'):
    y = {}
    for key in j:
        if key in TEXT_KEYS:
            d = recover_dict(j[key], splitor)
            for lang in d:
                y[key + '_' + lang] = d[lang]
        else:
            y[key] = j[key]
    return y


def yaml_item2json_dict(y):
    j = {}
    common = {}
    for key in y:
        if key.split('_')[0] in TEXT_KEYS:
            k, v = key.split('_', 1)
            if v not in j:
                j[v] = {}
            j[v][k] = y[key]
        else:
            common[key] = y[key]
    for lang in j:
        j[lang].update(common)
        for key in TEXT_KEYS:
            if key not in j[lang]:
                j[lang][key] = ''
    return j


def yaml2json_aio(yaml_aio, splitor='&&'):
    json_aio = []
    for yaml_mark in yaml_aio:
        json_aio.append(yaml_item2json_aio(yaml_mark, splitor))
    return json_aio


def yaml2json_by_key(yaml_aio, splitor='&&'):
    j = {}
    for yaml_mark in yaml_aio:
        d = yaml_item2json_dict(yaml_mark)
        for key in d:
            if key not in j:
                j[key] = []
            j[key].append(d[key])
    return j


def yaml_aio_to_json_all(path, splitor='&&', output=''):
    data_aio = load_yaml(path)  # marks.yaml
    base_dir = output if output else os.path.dirname(path)
    name, ext = os.path.splitext(os.path.basename(path))

    json_aio_path = os.path.join(base_dir, name + '.json')
    save_json(json_aio_path, yaml2json_aio(data_aio, splitor))
    json_by_key = yaml2json_by_key(data_aio)
    for key in json_by_key:
        json_path = os.path.join(base_dir, name + '_' + key + '.json')
        save_json(json_path, json_by_key[key])


def json_aio_to_yaml(path, splitor='&&', output=''):
    data_aio = load_json(path)  # marks.json
    base_dir = output if output else os.path.dirname(path)
    name, ext = os.path.splitext(os.path.basename(path))
    y = []
    for item in data_aio:
        y.append(json_aio_item2yaml(item, splitor))

    #y = sorted(y, key=lambda x: x.get('visiable_zoom_level', 0))
    yaml_aio_path = os.path.join(base_dir, name + '.yaml')
    save_yaml(yaml_aio_path, y)

# i18n config


def split_template(data):
    temps = {}
    for key in data:
        for lang, value in data[key].items():
            if lang not in temps:
                temps[lang] = {}
            temps[lang][key] = value
    return temps


def expand_i18n(path):
    i18n = load_yaml(path)
    base_dir = os.path.dirname(path)
    save_json(os.path.join(base_dir, 'mapping.json'), i18n['mapping'])
    templates = split_template(i18n['template'])
    for lang, t in templates.items():
        save_json(os.path.join(base_dir, lang + '.json'), t)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pzmap2dzi i18n tool')
    parser.add_argument('-o', '--output', type=str, default='')
    parser.add_argument('-s', '--splitor', type=str, default='&&')
    parser.add_argument('file', type=str, default='')
    args = parser.parse_args()

    basename = os.path.basename(args.file)
    if basename == 'i18n.yaml':
        expand_i18n(args.file)
    else:
        _, ext = os.path.splitext(args.file)
        if ext == '.yaml':
            yaml_aio_to_json_all(args.file, args.splitor, args.output)
        if ext == '.json':
            json_aio_to_yaml(args.file, args.splitor, args.output)
