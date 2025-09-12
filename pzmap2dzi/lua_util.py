import lupa
import os


def _is_list_keys(keys):
    length = len(keys)
    for key in keys:
        if type(key) is not int:
            return False
        if key < 1 or key > length:
            return False
    s = set(keys)
    if len(s) != length:
        return False
    return True


def unpack_lua_table(table, filter_type=None):
    type = lupa.lua_type(table)
    if filter_type and type in filter_type:
        return None
    if type != 'table':
        return table
    d = dict(table)
    keys = list(d.keys())
    isList = _is_list_keys(keys)
    output = {}
    if isList:
        output = [None] * len(keys)
    for key in keys:
        output_key = key - 1 if isList else key
        output[output_key] = unpack_lua_table(d[key], filter_type)
    return output


def run_lua_file(path, env=None, pre_code=None, post_code=None, work_dir=None):
    lua_code = ''
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as file:
            lua_code = file.read()
    if not pre_code:
        pre_code = ''
    if not post_code:
        post_code = ''
    code = '\n'.join([pre_code, lua_code, post_code])
    return run_lua_code(code, env=env, work_dir=work_dir)


def run_lua_code(lua_code, env=None, work_dir=None):
    cwd = None
    if work_dir:
        cwd = os.getcwd()
        os.chdir(work_dir)
    if env is None:
        env = lupa.LuaRuntime(unpack_returned_tuples=True)
    if lua_code:
        env.execute(lua_code)
    if work_dir:
        os.chdir(cwd)
    return env


def run_and_get_var(path_or_code=None, var_name=None,
                    work_dir=None, is_code=False):
    env = run_lua_code(None, work_dir=work_dir)
    default_globals = {}
    if not var_name:
        g = env.globals()
        default_globals = {key: g[key] for key in g.keys()}
    if os.path.isfile(path_or_code) and not is_code:
        run_lua_file(path_or_code, env=env, work_dir=work_dir)
    else:
        run_lua_code(path_or_code, env=env, work_dir=work_dir)
    if var_name:
        var = env.globals()[var_name]
        if var is None:
            return None
        return unpack_lua_table(var)
    else:
        g = env.globals()
        keys = list(g.keys())
        d = {}
        not_equal = env.eval('function (a, b) return a ~= b end')
        for k in keys:
            if k not in default_globals or not_equal(g[k], default_globals[k]):
                d[k] = unpack_lua_table(g[k])
            else:
                print('skip', k)
        return d


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, help='Path to the Lua file to run')
    args = parser.parse_args()
    env = run_lua_file(args.path)
