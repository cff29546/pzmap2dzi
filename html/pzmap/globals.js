export var g = {
    map_type: 'iso',
    overlays: {},
    mapui: 0,
    gridui: 0,
    trimmerui: 0,
    markerui: 0,
    aboutui: 0,
    currentLayer: 0,
    route: 'default',
    query_string: {},
    conf: {}
};

function updateQueryString() {
    g.query_string = {};
    let params = location.search.slice(1).split('&');
    for (let kv of params) {
        if (kv.indexOf('=') >= 0) {
            let [k, ...v] = kv.split('=');
            g.query_string[k] = v.join('=');
        }
    }
}

function loadConfig() {
    let p = window.fetch('./pzmap_config.json').then((r) => r.json());
    p = p.catch((e) => Promise.resolve({}));
    return p.then((data) => {
        g.conf = data;
        return Promise.resolve(data);
    });
}

export function reset() {
    g.viewer = 0;
    g.base_map = 0;
    g.mod_maps = [];
    g.roof_opacity = 0;
    g.minLayer = 0;
    g.maxLayer = 0;
    g.grid = 0;
    updateQueryString();
};

export function getRoot(name=null) {
    // Name is obtained in the following order of precedence:
    // 1. query string (online environment)
    // 2. g.route (offline environment, using selector)
    // 3. '' empty for default
    if (name === null) {
        name = g.query_string.map_name;
        if (!name) {
            name = g.route;
        }
        if (!name) {
            name = '';
        }
    }
    let path = name;
    let route = g.conf.route;
    if (route) {
        path = route[name];
    }
    if (!path) {
        path = name;
    }
    return path;
}

export function init() {
    return loadConfig();
}
