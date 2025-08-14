var g; // globals vars
var globals; // module
var map; // module
var c; // module coordinates
var util; // module
var i18n; // module
var ui; // module
var marker; // module
var Trimmer;
var pmodules = [
    import("./pzmap/globals.js").then((m) => {
        g = m.g;
        globals = m;
        return m.init();
    }),
    import("./pzmap/map.js").then((m) => {
        map = m;
    }),
    import("./pzmap/coordinates.js").then((m) => {
        c = m;
    }),
    import("./pzmap/marker.js").then((m) => {
        marker = m;
    }),
    import("./pzmap/trimmer.js").then((m) => {
        Trimmer = m.Trimmer;
    }),
    import("./pzmap/i18n.js").then((m) => {
        i18n = m;
        return m.init();
    }),
    import("./pzmap/util.js").then((m) => {
        util = m;
    }),
    import("./pzmap/ui.js").then((m) => {
        ui = m;
    })
];

window.addEventListener("keydown", (event) => {onKeyDown(event);});

function initUI() {
    g.UI = ui.createUI();
    util.changeStyle('.iso-only-btn', 'display', g.map_type == 'top' ? 'none' : 'inline-block');
    if (g.map_type == 'top') {
        document.getElementById('change_view_btn').innerHTML = 'Switch to Isometric View';
        g.overlays.room = 0;
        g.overlays.objects = 0;
    } else {
        document.getElementById('change_view_btn').innerHTML = 'Switch to Top View';
    }
    updateLayerSelector();
    for (const type of ['zombie', 'foraging', 'room', 'objects']) {
        const uiContainer = document.getElementById(type + '_ui');
        const btn = document.getElementById(type + '_btn');
        if (g.overlays[type]) {
            if (uiContainer) {
                uiContainer.innerHTML = g.UI[type].html;
            }
            if (btn) {
                btn.classList.add('active');
            }
        } else {
            if (uiContainer) {
                uiContainer.innerHTML = '';
            }
            if (btn) {
                btn.classList.remove('active');
            }
        }
    }
    for (const type of ['marker', 'grid', 'map', 'trimmer', 'about']) {
        const uiContainer = document.getElementById(type + '_ui');
        const btn = document.getElementById(type + '_btn');
        if (g[type + 'ui']) {
            if (uiContainer) {
                uiContainer.innerHTML = g.UI[type].html;
            }
            if (btn) {
                if (type == 'map') {
                    btn.classList.remove('active');
                } else {
                    btn.classList.add('active');
                }
            }
        } else {
            if (uiContainer) {
                uiContainer.innerHTML = '';
            }
            if (btn) {
                btn.classList.remove('active');
            }
        }
    }
    if (g.mapui) {
        initModMapUI();
    }
    if (g.overlays.foraging || g.overlays.objects) {
        document.getElementById('legends').style.display = '';
    } else {
        document.getElementById('legends').style.display = 'none';
    }

    let changeView = false;
    for (const type of g.base_map.available_types) {
        if (type != g.base_map.type) {
            changeView = true;
        }
    }
    if (changeView) {
        document.getElementById('change_view_btn').style.display = '';
    } else {
        document.getElementById('change_view_btn').style.display = 'none';
    }


    updateLangSelector();
    updateRouteSelector();
    if (g.aboutui) {
        updateAbout();
    }

    util.setOutput('main_output', 'Green', '');
    document.body.style.background = 'black';
}

function updateMainOutput() {
    if (g.load_error) {
        util.setOutput('main_output', 'red', '<b>' + i18n.E('MapMissingType') + '</b>');
    } else {
        util.setOutput('main_output', 'green', '');
    }
}

function initOSD() {
    g.load_error = 0;
    const options = {
        drawer: 'canvas',
        opacity: 1,
        element: document.getElementById('map_div'),
        tileSources: globals.getRoot() + 'base' + g.base_map.suffix + '/layer0.dzi',
        homeFillsViewer: true,
        showZoomControl: true,
        constrainDuringPan: true,
        visibilityRatio: 0.5,
        prefixUrl: 'openseadragon/images/',
        navigatorBackground: 'black',
        minZoomImageRatio: 0.5,
        maxZoomPixelRatio: 2 * g.base_map.scale
    };
    if (g.base_map.type == 'top') {
        options.imageSmoothingEnabled = false;
        options.maxZoomPixelRatio = 16 * g.base_map.scale;
    }
    g.viewer = OpenSeadragon(options);

    g.viewer.addHandler('add-item-failed', (event) => {
        g.load_error = 1;
        updateMainOutput();
    });

    g.viewer.addHandler('update-viewport', function() {
        g.grid.update(g.viewer);

        if (g.trimmerui) {
            g.grid.drawEditState(g.trimmer, g.currentLayer);
        }

        if (g.gridui || g.trimmerui) {
            g.grid.draw(g.currentLayer);
        }

        if (g.marker) {
            g.marker.redrawAll();
        }

        if (g.sys_marker) {
            g.sys_marker.redrawAll();
        }
    });

    g.viewer.addHandler('zoom', function(event) {
        if (marker.zoom()) {
            forceRedraw();
        }
    });

    g.viewer.addHandler('canvas-press', function(event) {
        if (g.trimmerui) {
            if (g.trimmer.press(event)) {
                event.preventDefaultAction = true;
            }
        }

        if (g.markerui) {
            if (g.marker.press(event)) {
                event.preventDefaultAction = true;
            }
        }
    });

    g.viewer.addHandler('canvas-drag', function(event) {
        if (g.trimmerui) {
            if (g.trimmer.drag(event)) {
                forceRedraw();
                event.preventDefaultAction = true;
            }
        }
        if (g.markerui) {
            if (g.marker.drag(event)) {
                forceRedraw();
                event.preventDefaultAction = true;
            }
        }
    });

    g.viewer.addHandler('canvas-release', function(event) {
        if (g.trimmerui) {
            if (g.trimmer.release(event)) {
                forceRedraw();
                event.preventDefaultAction = true;
            }
        }
        if (g.markerui) {
            if (g.marker.release(event)) {
                forceRedraw();
                event.preventDefaultAction = true;
            }
        }

    });

    g.viewer.addHandler('canvas-click', function(event) {
        if (event.quick) {
            if (g.trimmerui) {
                g.trimmer.click(event);
                forceRedraw();
                event.preventDefaultAction = true;
            }
            if (g.markerui) {
                if (g.marker.click(event)) {
                    event.preventDefaultAction = true;
                }
            }
        }
    });

    g.viewer.addHandler('canvas-scroll', function(event) {
        if (event.originalEvent.shiftKey) {
            g.currentLayer += event.scroll;
            updateLayerSelector();
            onLayerSelect();
            event.preventDefaultAction = true;
        }
    });

    if (g.map_type == 'top') {
        g.viewer.drawer.context.mozImageSmoothingEnabled = false;
        g.viewer.drawer.context.webkitImageSmoothingEnabled = false;
        g.viewer.drawer.context.msImageSmoothingEnabled = false;
        g.viewer.drawer.context.imageSmoothingEnabled = false;
    }
}

function init(callback=null) {
    globals.reset();
    if (!g.marker) {
        g.marker = new marker.MarkManager({ indexType: 'rtree' });
    } else {
        g.marker.clearRenderCache();
    }
    if (!g.sys_marker) {
        g.sys_marker = new marker.MarkManager({ onlyCurrentLayer: true });
    } else {
        g.sys_marker.clearRenderCache();
    }
    if (!g.trimmer) {
        g.trimmer = new Trimmer();
    }
    g.base_map = new map.Map(globals.getRoot(), g.map_type, '');
    return g.base_map.init().then(function(b) {
        g.map_type = b.type;
        g.grid = new c.Grid(b);
        initUI();
        updateClip();
        initOSD();
        i18n.update('id');
        g.marker.changeMode();
        //g.sys_marker.changeMode(); // sys_marker does not use rtree index, always 'top' mode

        return new Promise(function(resolve, reject) {
            g.viewer.addOnceHandler('tile-loaded', function(e) {
                let p = new Promise(function(res, rej) {
                    const img = e.tiledImage;
                    img.addOnceHandler('fully-loaded-change', function(e) {
                        img.setOpacity(0);
                        res();
                    });
                });
                g.viewer.canvas.addEventListener('pointermove', onPointerMove);
                updateMaps(g.currentLayer);
                g.marker.redrawAll();
                if (callback) {
                    p = Promise.all([p, callback()]);
                }
                p.then(() => { resolve(e); });
            });
        });
    });
}

function forceRedraw() {
    g.viewer.forceRedraw();
    g.viewer.raiseEvent('update-viewport', {});
}

// layer selector
function updateLayerSelector() {
    const s = document.getElementById('layer_selector')
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }
    g.minLayer = g.base_map.minlayer;
    g.maxLayer = g.base_map.maxlayer;
    for (const mod_map of g.mod_maps) {
        if (g.minLayer > mod_map.minlayer) {
            g.minLayer = mod_map.minlayer;
        }
        if (g.maxLayer < mod_map.maxlayer) {
            g.maxLayer = mod_map.maxlayer;
        }
    }
    for (let i = g.minLayer; i < g.maxLayer; i++) {
        const o = document.createElement('option');
        o.value = i;
        o.text = i18n.E('Floor', i);
        s.appendChild(o);
    }
    if (g.currentLayer >= g.maxLayer) {
        g.currentLayer = g.maxLayer - 1;
    }
    if (g.currentLayer < g.minLayer) {
        g.currentLayer = g.minLayer;
    }
    s.selectedIndex = g.currentLayer - g.minLayer;
}

function onLayerSelect() {
    const layer = Number(document.getElementById('layer_selector').value);
    updateMaps(layer);
    updateCoords(true);
    g.marker.redrawAll();
}

// roof opacity
function updateRoofOpacity() {
    const slider = document.getElementById('roof_opacity_slider');
    g.roof_opacity = slider.value;
    slider.title = i18n.E('RoofOpacity');
    updateMaps(g.currentLayer);
}

// mod map ui
function toggleModMapUI() {
    if (g.mapui) {
        g.mapui = 0;
        document.getElementById('map_ui').innerHTML = '';
    } else {
        g.mapui = 1;
        document.getElementById('map_ui').innerHTML = g.UI.map.html;
        initModMapUI();
    }
}

function initModMapUI() {
    let p = window.fetch(globals.getRoot() + 'mod_maps/map_list.json');
    p = p.then((r) => r.json()).catch((e)=>Promise.resolve([]));
    p = p.then((map_names) => {
        const s = document.getElementById('map_selector')
        for (const name of map_names) {
            const o = document.createElement('option');
            o.value = name;
            o.text = name;
            s.appendChild(o);
        }
        updateModMapUI();
    });
    return p;
}

function updateModMapUI() {
    if (g.mapui) {
        const btn = document.getElementById('map_all_btn');
        if (g.mod_maps.length > 0) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
        i18n.update('id', g.UI.map.ids)
        const mapListContainer = document.getElementById('map_list');
        mapListContainer.innerHTML = '';
        const warning = [];
        for (const mod_map of g.mod_maps) {
            let state = 'active';
            if (mod_map.pz_version != g.base_map.pz_version) {
                state = 'warning';
                warning.push(mod_map.name)
            }
            mapListContainer.innerHTML += `<button class="${state}" style="cursor: not-allowed" ` +
                `onclick="removeMap('${mod_map.name.replace("'","\\'")}')">${mod_map.name}</button>`;
        }

        if (warning.length > 0) {
            util.setOutput('map_output', 'red', '<b>' + i18n.T('MapErrorVersion') + '</b> ' + warning.join(','), 5000);
        }
    }
}

function updateClip() {
    g.base_map.setClipByOtherMaps(g.mod_maps, g.currentLayer);
    for (let i = 0; i < g.mod_maps.length; i++) {
        g.mod_maps[i].setClipByOtherMaps(g.mod_maps.slice(i + 1), g.currentLayer);
    }
}

function updateMaps(layer) {
    g.base_map.setBaseLayer(layer);
    g.base_map.setOverlayLayer(g.overlays, layer);
    for (let i = 0; i < g.mod_maps.length; i++) {
        g.mod_maps[i].setBaseLayer(layer);
        g.mod_maps[i].setOverlayLayer(g.overlays, layer);
    }
    g.currentLayer = layer;
}

function removeMap(name) {
    let pos = 0;
    for (pos = 0; pos < g.mod_maps.length; pos++) {
        if (name == g.mod_maps[pos].name) {
            break;
        }
    }
    if (pos < g.mod_maps.length) {
        g.mod_maps[pos].destroy();
        g.mod_maps.splice(pos, 1);
        if (g.mod_maps.length == 0) {
            document.getElementById('map_btn').classList.remove('active');
        }
        updateModMapUI();
        updateClip();
        updateLayerSelector();
    }
}

function addMap(names) {
    const p = [];
    for (const name of names) {
        if (name != '') {
            let pos = 0;
            for (pos = 0; pos < g.mod_maps.length; pos++) {
                if (name === g.mod_maps[pos].name) {
                    break;
                }
            }
            if (pos >= g.mod_maps.length) {
                const m = new map.Map(globals.getRoot() + 'mod_maps/' + name + '/', g.map_type, name, g.base_map);
                g.mod_maps.push(m);
                p.push(m.init());
                if (g.mod_maps.length == 1) {
                    document.getElementById('map_btn').classList.add('active');
                }
            }
        }
    }

    return Promise.all(p).then(function (maps) {
        updateModMapUI();
        updateClip();
        updateMaps(g.currentLayer);
        updateLayerSelector();
    });
}

function toggleAllMaps() {
    if (g.mapui) {
        if (g.mod_maps.length > 0) {
            for (pos = 0; pos < g.mod_maps.length; pos++) {
                g.mod_maps[pos].destroy();
            }
            g.mod_maps = [];
            document.getElementById('map_btn').classList.remove('active');
            updateModMapUI();
            updateClip();
            updateLayerSelector();
        } else {
            const s = document.getElementById('map_selector');
            const names = [];
            for (const o of s.options) {
                if (o.value) {
                    names.push(o.value);
                }
            }
            addMap(names);
        }
    }
}

function onMapSelect() {
    if (g.mapui) {
        const s = document.getElementById('map_selector');
        addMap([s.value]);
        s.value = '';
    }
}

// grid
function toggleGrid() {
    if (g.gridui) {
        g.gridui = 0;
        document.getElementById('grid_btn').classList.remove('active');
    } else {
        g.gridui = 1;
        document.getElementById('grid_btn').classList.add('active');
        g.viewer.raiseEvent('update-viewport', {});
    }
    forceRedraw();
}

// overlay maps
function toggleOverlay(type) {
    g.overlays[type] = !g.overlays[type];
    if (g.overlays[type]) {
        document.getElementById(type + '_btn').classList.add('active');
        const uiContainer = document.getElementById(type + '_ui');
        if (uiContainer) {
            uiContainer.innerHTML = g.UI[type].html;
            i18n.update('id', g.UI[type].ids);
        }
    } else {
        document.getElementById(type + '_btn').classList.remove('active');
        const uiContainer = document.getElementById(type + '_ui');
        if (uiContainer) {
            uiContainer.innerHTML = '';
        }
    }
    if (g.overlays.foraging || g.overlays.objects) {
        document.getElementById('legends').style.display = '';
    } else {
        document.getElementById('legends').style.display = 'none';
    }

    updateMaps(g.currentLayer);
}

// marker
function toggleMarkerUI() {
    if (g.markerui) {
        g.markerui = 0;
        document.getElementById('marker_btn').classList.remove('active');
        document.getElementById('marker_ui').innerHTML = '';
        g.marker.unSelect();
    } else {
        g.markerui = 1;
        g.markerui_help = 0;
        document.getElementById('marker_btn').classList.add('active');
        document.getElementById('marker_ui').innerHTML = g.UI.marker.html;
        i18n.update('id', g.UI.marker.ids);
        if (g.trimmerui) {
            toggleTrimmer();
        }
        g.marker.update();
    }
}

function toggleMarkerHelp() {
    if (g.markerui) {
        const help = document.getElementById('marker_help');
        if (g.markerui_help) {
            help.innerHTML = '';
            g.markerui_help = 0;
        } else {
            help.innerHTML = g.UI.marker_help.html;
            g.markerui_help = 1;
        }
        i18n.update('id', g.UI.marker_help.ids);
    }
    return false;
}

function onMarkerSave() {
    g.marker.save();
}

function onMarkerDelete(event) {
    if (event && event.ctrlKey) {
        g.marker.removeSelectedSingle();
    } else {
        g.marker.removeSelected();
    }
}

function onMarkerImport() {
    g.marker.Import();
}

function onMarkerExport() {
    g.marker.Export();
}

function onMarkerDefault() {
    g.marker.loadDefault();
}

function onMarkerClear() {
    g.marker.removeAll();
}

function onMarkerFocus() {
    g.marker.focusSelected();
}

function onMarkerDeselect() {
    g.marker.unSelect();
    g.marker.update();
}

function onMarkerInput(e) {
    g.marker.Input(e);
}

function togglePointMark(e) {
    if (e.checked) {
        g.marker.setVisiableType('Point', true);
    } else {
        g.marker.setVisiableType('Point', false);
    }
}

function toggleAreaMark(e) {
    if (e.checked) {
        g.marker.setVisiableType('Area', true);
    } else {
        g.marker.setVisiableType('Area', false);
    }
}

function toggleMarkName(e) {
    if (e.checked) {
        g.marker.setTextVisibility(true);
    } else {
        g.marker.setTextVisibility(false);
    }
}

// trimmer ui
function toggleTrimmer() {
    if (g.trimmerui) {
        g.trimmerui = 0;
        document.getElementById('trimmer_btn').classList.remove('active');
        document.getElementById('trimmer_ui').innerHTML = '';
    } else {
        g.trimmerui = 1;
        g.trimmerui_help = 0;
        document.getElementById('trimmer_btn').classList.add('active');
        document.getElementById('trimmer_ui').innerHTML = g.UI.trimmer.html;
        i18n.update('id', g.UI.trimmer.ids);
        if (g.markerui) {
            toggleMarkerUI();
        }
        g.trimmer.listSave();
    }
    forceRedraw();
}

function toggleTrimmerHelp() {
    if (g.trimmerui) {
        const help = document.getElementById('trimmer_help');
        if (g.trimmerui_help) {
            help.innerHTML = '';
            g.trimmerui_help = 0;
        } else {
            help.innerHTML = g.UI.trimmer_help.html;
            g.trimmerui_help = 1;
        }
        i18n.update('id', g.UI.trimmer_help.ids);
    }
    return false;
}

function onTrimmerRefresh() {
    if (g.trimmerui) {
        g.trimmer.listSave().then(() => {
            forceRedraw();
        });
    }
}

function onTrimmerSaveSelect() {
    if (g.trimmerui) {
        g.trimmer.save_path = document.getElementById('trimmer_save_selector').value;
        g.trimmer.loadSave().then(() => {
            forceRedraw();
        });
    }
}

function onTrimmerBrowse() {
    g.trimmer.browse();
}

function onTrim() {
    if (g.trimmerui) {
        g.trimmer.trim().then((update) => {
            if (update) {
                forceRedraw();
            }
        });
    }
}

// coordinates
function copyCoords() {
    const coords = '(' + g.sx + ',' + g.sy + ')';
    util.setClipboard(coords).then((err) => {
        if (err) {
            util.setOutput('main_output', 'Red', i18n.T('CopyCoordsError', {error: err}));
        } else {
            let e = document.getElementById('coords');
            e.style['border-color'] = 'Green';
            util.setOutput('coords', 'Green', i18n.T('CopyCoordsSuccess'));
        }
    });
}

function updateCoords(recalc=false) {
    if (recalc && g.position) {
        [g.sx, g.sy] = c.getSquare(g.position);
    }
    const e = document.getElementById('coords');
    e.style['border-color'] = '';
    e.style['color'] = '';
    e.innerHTML = i18n.E('Coords');
    g.sys_marker.load([{
        id: 'cursor',
        rects: [{
            x: g.sx,
            y: g.sy,
            width: 1,
            height: 1
        }],
        layer: g.currentLayer,
        type: 'area',
        class_list: ['cursor'],
        passthrough: true,
        visiable_zoom_level: 2
    }], false);
}

function onPointerMove(event) {
    const mouse = OpenSeadragon.getMousePosition(event);
    const offset = OpenSeadragon.getElementOffset(g.viewer.canvas);
    g.position = {position: mouse.minus(offset)};
    updateCoords(true);
}

// change route
function updateRouteSelector() {
    const s = document.getElementById('route_selector');
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }

    s.style.display = 'none';
    if (g.query_string.map_name !== undefined) {
        return false;
    }
    const route = g.conf.route;
    if (!route) {
        return false;
    }

    const keys = Object.keys(route);
    if (keys.length <= 0) {
        return false;
    }
    if (keys.length === 1 && keys[0] === g.route) {
        return false;
    }

    if (!keys.includes(g.route)) {
        const o = document.createElement('option');
        o.id = "route_selector_dummy_option";
        o.value = 'default';
        o.text = i18n.T('SelectRoute');
        o.selected = true;
        s.appendChild(o);
    }
    for (const key of keys) {
        const o = document.createElement('option');
        o.value = key;
        o.text = key;
        if (g.route === key) {
            o.selected = true;
        }
        s.appendChild(o);
    }
    s.style.display = '';
}

function onChangeRoute() {
    const route = document.getElementById('route_selector').value;
    if (route !== g.route) {
        g.route = route;
        return reloadView(false);
    }
}

// change view
function onChangeView() {
    if (g.map_type == 'top') {
        g.map_type = 'iso';
    } else {
        g.map_type = 'top';
    }
    return reloadView(true);
}

function reloadView(keep_mod_map=false) {
    g.viewer.destroy();
    let setup_maps = null;
    if (keep_mod_map) {
        const map_names = [];
        for (const mod_map of g.mod_maps) {
            map_names.push(mod_map.name);
        }
        setup_maps = function () {
            addMap(map_names);
            return Promise.resolve();
        }
    }
    return init(setup_maps);
}

// language selector
function updateLangSelector() {
    const s = document.getElementById('language_selector')
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }

    for (const l of i18n.ALL) {
        const o = document.createElement('option');
        o.value = l;
        o.text = l;
        if (l === i18n.getLang()) {
            o.selected = true;
        }
        s.appendChild(o);
    }
}

function onChangeLanguage() {
    const lang = document.getElementById('language_selector').value;
    i18n.setLang(lang);
    i18n.update('id');
    updateLayerSelector();
    updateCoords();
    if (g.aboutui) {
        updateAbout();
    }
    if (g.trimmerui) {
        util.setOutput('trimmer_output', 'Green', '');
    }
    if (g.markerui) {
        g.marker.update();
    }
    updateMainOutput();
}

// about
function toggleAbout() {
    if (g.aboutui) {
        g.aboutui = 0;
        document.getElementById('about_btn').classList.remove('active');
        document.getElementById('about_ui').innerHTML = '';
    } else {
        g.aboutui = 1;
        document.getElementById('about_btn').classList.add('active');
        updateAbout();
    }
}

function updateAbout() {
    const [ids, html] = ui.genAboutUI();
    document.getElementById('about_ui').innerHTML = html;
    i18n.update('id', ids);
}

// key listener
function onKeyDown(event) {
    if (event.key == 'Escape' && g.markerui) {
        g.marker.unSelect();
        g.marker.update();
    }
    if (event.key == 'c') {
        copyCoords();
    }
    if (g.query_string.debug && event.key == 't') {
        // debug: test canvas range
        const r = c.getCanvasRange(g.viewer, g.base_map, g.currentLayer);
        g.marker.load([
            { type: 'area', id: 'range', layer: g.currentLayer, visiable_zoom_level: 0,
                rects: [{x: r.minX, y: r.minY, width: r.maxX - r.minX, height: r.maxY - r.minY}] },
            { type: 'point', id: 'range-tl', x: r.minX, y: r.minY, layer: g.currentLayer, visiable_zoom_level: 0 },
            { type: 'point', id: 'range-br', x: r.maxX, y: r.maxY, layer: g.currentLayer, visiable_zoom_level: 0 },
        ]);
    }
}

Promise.all(pmodules).then(() => {
    init();
}).catch((e) => {
    const output = document.getElementById('main_output');
    if (output) {
        output.style.color = 'red';
        output.innerHTML = 'Failed to initialize modules.<br/>Error: ' + e;
    }
    document.body.style.background = 'white';
    throw e;
});
