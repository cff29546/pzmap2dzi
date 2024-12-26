import os
import io
import shutil
import ruamel.yaml
import sys


def copy(dst, src, name, new_name=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    if not new_name:
        new_name = name
    source = os.path.join(src, name)
    target = os.path.join(dst, new_name)
    shutil.copy(source, target)


def update_data(data, update):
    for key, value in update.items():
        if isinstance(value, dict):
            data[key] = update_data(data.get(key, {}), value)
        else:
            data[key] = value
    return data


def update_conf(path, update):
    yaml = ruamel.yaml.YAML()
    if os.path.exists(path):
        with io.open(path, 'r', encoding='utf8') as f:
            conf = yaml.load(f.read())
    else:
        conf = {}
    conf = update_data(conf, update)
    with io.open(path, 'w', encoding='utf8') as f:
        yaml.dump(conf, f)


class ExampleConf(object):
    def __init__(self, output_path, conf_path):
        self.output = output_path
        self.conf = conf_path

    def __call__(self, name, update):
        conf = 'conf_{}.yaml'.format(name)
        copy(self.output, self.conf, 'conf.yaml', conf)
        update_conf(os.path.join(self.output, conf), update)


def get_all_mod_maps(conf):
    mod_path = os.path.join(conf, 'mod')
    data = []
    for name in os.listdir(mod_path):
        if name.endswith('.txt'):
            with io.open(os.path.join(mod_path, name), 'r', encoding='utf8') as f:
                data.append(f.read())
    import yaml
    mod = yaml.safe_load('\n'.join(data))
    output = []
    for name, value in mod.items():
        if isinstance(value, dict) and value.get('map_name'):
            output.append(name)
    return output


if __name__ == '__main__':
    current = os.path.dirname(__file__)
    output = os.path.join(current, 'output', 'examples')
    conf = os.path.join(current, '..', 'conf')

    e = ExampleConf(output, conf)
    e('stop_with_f9', {'render_conf': {'break_key': '<f9>'}})
    e('omit_2_levels', {'render_conf': {'omit_levels': 2}})
    e('no_base_map', {'base_map': None, 'mod_maps': ['BedfordFalls']})
    e('all_mod_maps', {'mod_maps': get_all_mod_maps(conf)})
    e('mod_maps', {'mod_maps': [
        'Ashenwood',
        'BedfordFalls',
        'Blueberry',
        'Chinatown',
        'Chinatown expansion',
        'FORTREDSTONE',
        'Grapeseed',
        'Greenleaf',
        'lakeivytownship',
        'Petroville',
        'RavenCreek',
        'Trelai_4x4_Steam',
    ]})
