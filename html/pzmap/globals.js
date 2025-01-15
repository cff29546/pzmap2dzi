export var g = {
    map_type: 'iso',
    overlays: {},
    mapui: 0,
    gridui: 0,
    trimmerui: 0,
    markerui: 0,
    aboutui: 0,
    currentLayer: 0
};
export function initGlobals() {
    g.viewer = 0;
    g.base_map = 0;
    g.mod_maps = [];
    g.roof_opacity = 0;
    g.minLayer = 0;
    g.maxLayer = 0;
    g.grid = 0;
};
