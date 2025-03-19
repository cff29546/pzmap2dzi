var g; // globals vars
var globals; // module
var map; // module
var c; // module coordinates
var util; // module
var i18n; // module
var Marker;
var Trimmer;
var debug = {};
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
        Marker = m.Marker;
        debug.marker = m;
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
    })
];

window.addEventListener("keydown", (event) => {onKeyDown(event);});

var LEGEND_TEMPLATE = {
    foraging: '<div class="legend" style="background-color:{color}"></div><span id="{id}"></span>',
    objects: '<div class="legend" style="border-color:{color}; border-width: 3px;"></div><span id="{id}"></span>'
};
function genLegendsUI(type, mapping) {
    let label_id = type + '_legends_text';
    let id = [label_id];
    let ui = '<b id="' + label_id + '"></b>';

    template = LEGEND_TEMPLATE[type];
    if (template) {
        for (let key in mapping) {
            let color = mapping[key];
            if (color == 'skip') {
                continue;
            }
            let legend_id = type + '_legend_' + key;
            ui += util.format(template, {color: color, id: legend_id});
            id.push(legend_id);
        }
    }
    return [id, ui];
}

function initUI_HTML() {
    g.UI_HTML = {};
    g.UI_ID = {};

    g.UI_HTML.map = `
<button id="map_all_btn" onclick="toggleAllMaps()"></button>
<select id="map_selector" onchange="onMapSelect()">
    <option id="map_selector_dummy_option" value=""></option>
</select>
<b id="map_loaded_text"></b>
<div id="map_list" style="display: inline-block"></div>
<div id="map_output" style="display: inline-block"></div>`;
    g.UI_ID.map = ['map_all_btn', 'map_selector_dummy_option', 'map_loaded_text'];

    let legends;
    legends = util.getByPath(g, 'base_map', 'info', 'foraging', 'legends');
    if (!legends) {
        legends = {Nav: 'White', TownZone: 'Blue', TrailerPark: 'Cyan', Vegitation: 'Yellow', Forest: 'Lime', DeepForest: 'Green', FarmLand: 'Magenta', Farm: 'Red'}
    }
    [g.UI_ID.foraging, g.UI_HTML.foraging] = genLegendsUI('foraging', legends);
    g.UI_HTML.foraging += `<span>&emsp; &emsp;</span>`;

    legends = util.getByPath(g, 'base_map', 'info', 'objects', 'legends');
    if (!legends) {
        legends = {ZombiesType: 'Red', ParkingStall: 'Blue', ZoneStory: 'Yellow'}
    }
    [g.UI_ID.objects, g.UI_HTML.objects] = genLegendsUI('objects', legends);

    g.UI_HTML.marker = `
<div style="display: flex">
<div style="display: inline-block">
    <table style="white-space: nowrap; text-align: right">
    <tr>
        <td><button id="marker_save_btn" type="button" style="width: 100%" onclick="onMarkerSave()">Save</button></td>
        <td id="marker_x_text">x:</td>
        <td><input id="marker_x" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td id="marker_y_text">y:</td>
        <td><input id="marker_y" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td style="display: flex;">
            <span id="marker_layer_text">layer:</span><input id="marker_layer" type="number" step="1" style="width: 3em" onchange="onMarkerInput(this)" />
            <span id="marker_name_text">name:</span> <input id="marker_name" type="text" style="flex: 1;" onchange="onMarkerInput(this)"/>
        </td>
        <td id="marker_description_text">description:</td>
    </tr>
    <tr>
        <td><button id="marker_delete_btn" type="button" onclick="onMarkerDelete()" style="width: 100%">Delete</button></td>
        <td id="marker_width_text">width:</td>
        <td><input id="marker_width" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td id="marker_height_text">height:</td>
        <td><input id="marker_height" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td class="text-right">
            <input type="checkbox" id="marker_hide" onchange="onMarkerInput(this)">
            <label id="marker_hide_label" for="marker_hide">Hide on zoom out</label>
            <button id="marker_import_btn" type="button" onclick="onMarkerImport()">Import</button>
            <button id="marker_export_btn" type="button" onclick="onMarkerExport()">Export</button>
            <button id="marker_default_btn" type="button" onclick="onMarkerDefault()">Load Default</button>
            <button id="marker_clear_btn" type="button" onclick="onMarkerClear()">Remove All</button>
        </td>
        <td><a id="marker_help_btn" href="" onclick="return toggleMarkerHelp();">Show Help</a></td>
    </tr>
    </table>
</div>
<div style="display: inline-block; width: 100%">
<table style="width: 100%"><td>
    <textarea id="marker_desc" rows="2" style="width: 100%; resize: none;" onchange="onMarkerInput(this)"></textarea>
</td></table>
</div>
</div>
<div style="display: flex;">
<button id="marker_deselect_btn" type="button" onclick="onMarkerDeselect()">Deselect(Esc)</button>
<input type="checkbox" id="marker_point" checked onchange="togglePointMark(this)">
<label id="marker_point_label" for="marker_point">Show Point</label>
<input type="checkbox" id="marker_area" checked onchange="toggleAreaMark(this)">
<label id="marker_area_label" for="marker_area">Show Area</label>
<div class="legend point" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_current">marks on this floor</span>
<div class="legend point above" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_above">marks above</span>
<div class="legend point below" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_below">marks below</span>
<div class="legend point selected" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_selected">the selected mark</span>
<span id="marker_output" class="inline" style="flex: 1; background-color: white; margin-left: 1em;"></span>
</div>
<div id="marker_help"></div>
    `;
    g.UI_HTML.marker_ID = [
        "marker_save_btn", "marker_x_text", "marker_y_text", "marker_layer_text", "marker_name_text", "marker_description_text",
        "marker_delete_btn", "marker_width_text", "marker_height_text", "marker_hide_label", "marker_import_btn", "marker_export_btn",
        "marker_default_btn", "marker_clear_btn", 'marker_help_btn', "marker_deselect_btn", "marker_point_label",
        "marker_area_label", "mark_current", "mark_above", "mark_below", "mark_selected"];

    g.UI_HTML.marker_help = '<div id="marker_help_text"></div>';
    g.UI_HTML.marker_help_ID = ['marker_help_btn', 'marker_help_text'];

    g.UI_HTML.trimmer = `
<b id="trimmer_title"></b> <span id="trimmer_legends_text"></span>
<div class="legend" style="background-color:#0f0"></div><span id="trimmer_saved"></span>
<div class="legend" style="background-color:#00f"></div><span id="trimmer_partial_saved"></span>
<div class="legend" style="background-color:#f00"></div><span id="trimmer_selected"></span>
<div class="legend" style="background-color:#ff0"></div><span id="trimmer_partial_selected"></span>
<a id="trimmer_help_btn" href="" class="text-right" onclick="return toggleTrimmerHelp();"></a>
<div>
<select id="trimmer_save_selector" onchange="onTrimmerSaveSelect()">
    <option id="trimmer_save_selector_dummy_option" value=""></option>
</select>
<button id="trimmer_refresh_btn" type="button" onclick="onTrimmerRefresh()"></button>
<input type="checkbox" id="trimmer_vehicles" checked>
<label id="trimmer_vehicles_label" for="trimmer_vehicles"></label>
<input type="checkbox" id="trimmer_animals">
<label id="trimmer_animals_label" for="trimmer_animals"></label>
<button id="trimmer_trim_btn" onclick="onTrim()"></button>
<div id="trimmer_output" style="display: inline-block"></div>
<button id="trimmer_browse_btn" class="text-right" onclick="onTrimmerBrowse()"></button>
</div>
<div id="trimmer_help"></div>`;
    g.UI_HTML.trimmer_ID = [
        "trimmer_title", "trimmer_legends_text", "trimmer_saved", "trimmer_partial_saved",
        "trimmer_selected", "trimmer_partial_selected", "trimmer_help_btn",
        "trimmer_save_selector_dummy_option", "trimmer_refresh_btn", "trimmer_vehicles_label",
        "trimmer_animals_label", "trimmer_trim_btn", "trimmer_browse_btn"];

    g.UI_HTML.trimmer_help = '<div id="trimmer_help_text"></div>';
    g.UI_HTML.trimmer_help_ID = ['trimmer_help_btn', 'trimmer_help_text'];
}

function initUI() {
    util.changeStyle('.iso', 'display', g.map_type == 'top' ? 'none' : '');
    if (g.map_type == 'top') {
        document.getElementById('change_view_btn').innerHTML = 'Switch to Isometric View';
        g.overlays.room = 0;
        g.overlays.objects = 0;
    } else {
        document.getElementById('change_view_btn').innerHTML = 'Switch to Top View';
    }
    updateLayerSelector();
    for (let type of ['zombie', 'foraging', 'room', 'objects']) {
        let ui = document.getElementById(type + '_ui');
        let btn = document.getElementById(type + '_btn');
        if (g.overlays[type]) {
            if (ui) {
                ui.innerHTML = g.UI_HTML[type];
            }
            if (btn) {
                btn.classList.add('active');
            }
        } else {
            if (ui) {
                ui.innerHTML = '';
            }
            if (btn) {
                btn.classList.remove('active');
            }
        }
    }
    for (let type of ['marker', 'grid', 'map', 'timmer', 'about']) {
        let ui = document.getElementById(type + '_ui');
        let btn = document.getElementById(type + '_btn');
        if (g[type + 'ui']) {
            if (ui) {
                ui.innerHTML = g.UI_HTML[type];
            }
            if (btn) {
                if (type == 'map') {
                    btn.classList.remove('active');
                } else {
                    btn.classList.add('active');
                }
            }
        } else {
            if (ui) {
                ui.innerHTML = '';
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

    let change_view = false;
    for (let type of g.base_map.available_types) {
        if (type != g.base_map.type) {
            change_view = true;
        }
    }
    if (change_view) {
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
    let options = {
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
    });

    g.viewer.addHandler('zoom', function(event) {
        if (g.marker.zoom()) {
            forceRedraw();
        }
    });

    g.viewer.addHandler('canvas-press', function(event) {
        if (g.trimmerui) {
            if (g.trimmer.press(event)) {
                //forceRedraw();
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
                let l = g.marker.click(event);
                if (l !== null) {
                    g.currentLayer = l;
                    updateLayerSelector();
                    onLayerSelect();
                }
                event.preventDefaultAction = true;
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

    g.viewer.canvas.addEventListener('pointermove', onPointerMove);
}

function init(callback=null) {
    globals.reset();
    if (!g.marker) {
        g.marker = new Marker();
    }
    if (!g.trimmer) {
        g.trimmer = new Trimmer();
    }
    g.base_map = new map.Map(globals.getRoot(), g.map_type, '');
    return g.base_map.init().then(function(b) {
        g.map_type = b.type;
        g.grid = new c.Grid(b);
        initUI_HTML();
        initUI();
        updateClip();
        initOSD();
        i18n.update('id');

        return new Promise(function(resolve, reject) {
            g.viewer.addOnceHandler('tile-loaded', function(e) {
                let p = new Promise(function(res, rej) {
                    let img = e.tiledImage;
                    img.addOnceHandler('fully-loaded-change', function(e) {
                        img.setOpacity(0);
                        res();
                    });
                });
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
    let s = document.getElementById('layer_selector')
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }
    g.minLayer = g.base_map.minlayer;
    g.maxLayer = g.base_map.maxlayer;
    for (let mod_map of g.mod_maps) {
        if (g.minLayer > mod_map.minlayer) {
            g.minLayer = mod_map.minlayer;
        }
        if (g.maxLayer < mod_map.maxlayer) {
            g.maxLayer = mod_map.maxlayer;
        }
    }
    for (let i = g.minLayer; i < g.maxLayer; i++) {
        let o = document.createElement('option');
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
    let layer = Number(document.getElementById('layer_selector').value);
    updateMaps(layer);
    g.marker.redrawAll();
}

// roof opacity
function updateRoofOpacity() {
    let slider = document.getElementById('roof_opacity_slider');
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
        document.getElementById('map_ui').innerHTML = g.UI_HTML.map;
        initModMapUI();
    }
}

function initModMapUI() {
    let p = window.fetch(globals.getRoot() + 'mod_maps/map_list.json');
    p = p.then((r) => r.json()).catch((e)=>Promise.resolve([]));
    p = p.then((map_names) => {
        let s = document.getElementById('map_selector')
        for (let name of map_names) {
            let o = document.createElement('option');
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
        let btn = document.getElementById('map_all_btn');
        if (g.mod_maps.length > 0) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
        i18n.update('id', g.UI_ID.map)
        let d = document.getElementById('map_list');
        d.innerHTML = '';
        let warning = [];
        for (let mod_map of g.mod_maps) {
            let state = 'active';
            if (mod_map.pz_version != g.base_map.pz_version) {
                state = 'warning';
                warning.push(mod_map.name)
            }
            d.innerHTML += `<button class="${state}" style="cursor: not-allowed" ` +
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
    let p = [];
    for (let name of names) {
        if (name != '') {
            let pos = 0;
            for (pos = 0; pos < g.mod_maps.length; pos++) {
                if (name === g.mod_maps[pos].name) {
                    break;
                }
            }
            if (pos >= g.mod_maps.length) {
                let m = new map.Map(globals.getRoot() + 'mod_maps/' + name + '/', g.map_type, name, g.base_map);
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
            let s = document.getElementById('map_selector');
            let names = [];
            for (let o of s.options) {
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
        let s = document.getElementById('map_selector');
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
        let ui = document.getElementById(type + '_ui');
        if (ui) {
            ui.innerHTML = g.UI_HTML[type];
            i18n.update('id', g.UI_ID[type]);
        }
    } else {
        document.getElementById(type + '_btn').classList.remove('active');
        let ui = document.getElementById(type + '_ui');
        if (ui) {
            ui.innerHTML = '';
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
        document.getElementById('marker_ui').innerHTML = g.UI_HTML.marker;
        i18n.update('id', g.UI_HTML.marker_ID);
        if (g.trimmerui) {
            toggleTrimmer();
        }
        g.marker.update();
    }
}

function toggleMarkerHelp() {
    if (g.markerui) {
        let t = document.getElementById('marker_help');
        if (g.markerui_help) {
            t.innerHTML = '';
            g.markerui_help = 0;
        } else {
            t.innerHTML = g.UI_HTML.marker_help;
            g.markerui_help = 1;
        }
        i18n.update('id', g.UI_HTML.marker_help_ID);
    }
    return false;
}

function onMarkerSave() {
    g.marker.save();
}

function onMarkerDelete() {
    g.marker.removeSelected();
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

function onMarkerDeselect() {
    g.marker.unSelect();
    g.marker.update();
}

function onMarkerInput(e) {
    g.marker.Input(e);
}

function togglePointMark(e) {
    if (e.checked) {
        util.changeStyle('.point', 'visibility', 'visible');
    } else {
        util.changeStyle('.point', 'visibility', 'hidden');
    }
}

function toggleAreaMark(e) {
    if (e.checked) {
        util.changeStyle('.area', 'visibility', 'visible');
    } else {
        util.changeStyle('.area', 'visibility', 'hidden');
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
        document.getElementById('trimmer_ui').innerHTML = g.UI_HTML.trimmer;
        i18n.update('id', g.UI_HTML.trimmer_ID);
        if (g.markerui) {
            toggleMarkerUI();
        }
        g.trimmer.listSave();
    }
    forceRedraw();
}

function toggleTrimmerHelp() {
    if (g.trimmerui) {
        let t = document.getElementById('trimmer_help');
        if (g.trimmerui_help) {
            t.innerHTML = '';
            g.trimmerui_help = 0;
        } else {
            t.innerHTML = g.UI_HTML.trimmer_help;
            g.trimmerui_help = 1;
        }
        i18n.update('id', g.UI_HTML.trimmer_help_ID);
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
    let coords = '(' + g.sx + ',' + g.sy + ')';
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

function updateCoords() {
    let e = document.getElementById('coords');
    e.style['border-color'] = '';
    e.style['color'] = '';
    e.innerHTML = i18n.E('Coords');
}

function onPointerMove(event) {
    let mouse = OpenSeadragon.getMousePosition(event);
    let offset = OpenSeadragon.getElementOffset(g.viewer.canvas);
    [g.sx, g.sy] = c.getSquare({position: mouse.minus(offset)});
    updateCoords();
}

// change route
function updateRouteSelector() {
    let s = document.getElementById('route_selector');
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }

    s.style.display = 'none';
    if (g.query_string.map_name !== undefined) {
        return false;
    }
    let route = g.conf.route;
    if (!route) {
        return false;
    }

    let keys = Object.keys(route);
    if (keys.length <= 0) {
        return false;
    }
    if (keys.length === 1 && keys[0] === g.route) {
        return false;
    }

    if (!keys.includes(g.route)) {
        let o = document.createElement('option');
        o.id = "route_selector_dummy_option";
        o.value = 'default';
        o.text = i18n.T('SelectRoute');
        o.selected = true;
        s.appendChild(o);
    }
    for (let key of keys) {
        let o = document.createElement('option');
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
    let route = document.getElementById('route_selector').value;
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
        let map_names = [];
        for (let mod_map of g.mod_maps) {
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
    let s = document.getElementById('language_selector')
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }

    for (let l of i18n.ALL) {
        let o = document.createElement('option');
        o.value = l;
        o.text = l;
        if (l === i18n.getLang()) {
            o.selected = true;
        }
        s.appendChild(o);
    }
}

function onChangeLanguage() {
    let lang = document.getElementById('language_selector').value;
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
    let div_begin = '<div style="display: inline-block; float: right; background-color: Yellow; text-align: left;">';
    let div_end = '</div>';
    let args = {};
    args.pzmap2dzi = '<a id="pzmap2dzi" href="https://github.com/cff29546/pzmap2dzi" target="_blank">pzmap2dzi</a>';
    args.osd = '<a id="osd" href="https://github.com/openseadragon/openseadragon" target="_blank">OpenSeaDragon</a>';
    args.pzwiki = '<a id="pzwiki" href="https://pzwiki.net/wiki/Project_Zomboid_Wiki" target="_blank">PZwiki</a>';
    args.pz = '<a id="pz" href="https://projectzomboid.com" target="_black">Project Zomboid</a>';
    args.pz_steam = '<a id="pz_steam" href="https://store.steampowered.com/app/108600/Project_Zomboid" target="_black">Project Zomboid</a>';
    args.pz_version = util.getByPath(g, 'base_map', 'pz_version');

    let link_template = '<a href="https://github.com/cff29546/pzmap2dzi/tree/{commit}" title="{branch}" target="_blank">{version}</a>';
    if (g.base_map.commit) {
        args.render_version = util.format(link_template, {
            commit: g.base_map.commit,
            branch: g.base_map.branch,
            version: g.base_map.render_version
        });
    } else {
        args.render_version = g.base_map.render_version;
    }
    if (g.conf.git_commit) {
        args.ui_version = util.format(link_template, {
            commit: g.conf.git_commit,
            branch: g.conf.git_branch,
            version: g.conf.version
        });
    } else {
        args.ui_version = g.conf.version;
    }
    let aboutUI = div_begin + i18n.T('About', args) + div_end;
    document.getElementById('about_ui').innerHTML = aboutUI;
    let aboutUI_ID = ['pzmap2dzi', 'osd', 'pzwiki', 'pz', 'pz_steam'];
    i18n.update('id', aboutUI_ID);
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
}

Promise.all(pmodules).then(() => {
    init();
}).catch((e) => {
    let output = document.getElementById('main_output');
    if (output) {
        output.style.color = 'red';
        output.innerHTML = 'Failed to initialize modules.<br/>Error: ' + e;
    }
    document.body.style.background = 'white';
    throw e;
});
