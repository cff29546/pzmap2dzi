var map_type = "iso";
var suffix = "";
var viewer = 0;

const Map = class {
    layers = 0;
    tiles = [];
    overlays = {};
    overlay_layer = 0;
    room = 0;
    foraging = 0;
    zombie = 0;
    objects = 0;
    x0 = 0;
    y0 = 0;
    sqr = 1;
    cell_rects = [];
    clip_list = [];

    constructor(name, is_base=false) {
        this.name = name;
        this.is_base = is_base;
        this.init();
    }

    cell2pixel(cx, cy) {
        let p = {}
        if (map_type == 'iso') {
            p.x = this.x0 + (cx - cy) * this.sqr * 150;
            p.y = this.y0 + (cx + cy) * this.sqr * 75;
        } else {
            p.x = this.x0 + cx * this.sqr * 300;
            p.y = this.y0 + cy * this.sqr * 300;
        }
        return p;
    }

    getClipPoints(rects, remove=true) {
        let points = [];
        if (remove) {
            points.push({x: 0, y: 0});
            points.push({x: 0, y: this.h});
            points.push({x: this.w, y: this.h});
            points.push({x: this.w, y: 0});
        }
        points.push({x: 0, y: 0});
        for (let [x, y, w, h] of rects) {
            points.push(this.cell2pixel(x, y));
            points.push(this.cell2pixel(x + w, y));
            points.push(this.cell2pixel(x + w, y + h));
            points.push(this.cell2pixel(x, y + h));
            points.push(this.cell2pixel(x, y));
            points.push({x: 0, y: 0});
        }
        return points;
    }

    setClipFromOverlayMaps(maps) {
        this.clip_list = [this.getClipPoints(this.cell_rects, false)];
        for (let i = maps.length - 1; i >= 0; i--) {
            let rlist = [];
            for (let r of maps[i].cell_rects) {
                for (let b of this.cell_rects) {
                    if (rectIntersect(b, r)) {
                        rlist.push(r);
                        break;
                    }
                }
            }
            if (rlist.length > 0) {
                this.clip_list.push(this.getClipPoints(rlist));
            }
        }
        
        for (let type of ['zombie', 'foraging']) {
            if (this.overlays[type]) {
                this.overlays[type].setCroppingPolygons(this.clip_list);
            }
        }
        for (let type of ['room', 'objects']) {
            if (this.overlays[type]) {
                let clip_list = shiftClipList(this.clip_list);
                this.overlays[type].setCroppingPolygons(clip_list);
            }
        }
    }

    getMapRoot() {
        if (this.is_base) {
            return '';
        }
        return 'mod_maps/' + this.name + '/'; 
    }

    _load(type, layer) {
        if (viewer) {
            let x = base_map.x0 - this.x0;
            let y = base_map.y0 - this.y0;
            let p = viewer.world.getItemAt(0).imageToViewportCoordinates(x, y);
            let width = this.w / base_map.w;
            if (type == 'base') {
                if (layer < this.layers && this.tiles[layer] == 0) {
                    this.tiles[layer] = null;
                    viewer.addTiledImage({
                        tileSource: this.getMapRoot() + type + suffix + "/layer" + layer + ".dzi",
                        opacity: 1,
                        x: p.x,
                        y: p.y,
                        width: width,
                        success: (function (obj) {
                            if (this.tiles[layer] == 'delete') {
                                viewer.world.removeItem(obj.item);
                                this.tiles[layer] = 0;
                            } else {
                                this.tiles[layer] = obj.item;
                                positionItem(obj.item, this.name, layer);
                            }
                        }).bind(this),
                        error: (function (e) {
                            if (['delete', 0, null].includes(this.tiles[layer])) {
                                this.tiles[layer] = 0;
                            }
                        }).bind(this),
                    });
                }
                return
            }
            let shift = true;
            if (type == 'zombie' || type == 'foraging') {
                layer = 0;
                shift = false;
            }
            if (this.overlays[type] == 0) {
                this.overlays[type] = null;
                viewer.addTiledImage({
                    tileSource: this.getMapRoot() + type + suffix + "/layer" + layer + ".dzi",
                    opacity: 1,
                    x: p.x,
                    y: p.y,
                    width: width,
                    success: (function (obj) {
                        if (this.overlays[type] == 'delete') {
                            viewer.world.removeItem(obj.item);
                            this.overlays[type] = 0;
                        } else {
                            this.overlays[type] = obj.item;
                            if (shift) {
                                let clip_list = shiftClipList(this.clip_list, layer);
                                this.overlays[type].setCroppingPolygons(clip_list);
                            } else {
                                this.overlays[type].setCroppingPolygons(this.clip_list);
                            }
                        }
                    }).bind(this),
                    error: (function (e) {
                        if (['delete', 0, null].includes(this.overlays[type])) {
                            this.overlays[type] = 0;
                        }
                    }).bind(this),
                });
            }
        }
    }

    _unload(type, layer) {
        if (viewer) {
            if (type == 'base') {
                if (layer < this.layers && this.tiles[layer] != 0) {
                    if ([null, 'delete'].includes(this.tiles[layer])) {
                        this.tiles[layer] = 'delete';
                    } else {
                        viewer.world.removeItem(this.tiles[layer]);
                        this.tiles[layer] = 0;
                    }
                }
                return
            }
            if (this.overlays[type] != 0) {
                if ([null, 'delete'].includes(this.overlays[type])) {
                    this.overlays[type] = 'delete';
                } else {
                    viewer.world.removeItem(this.overlays[type]);
                    this.overlays[type] = 0;
                }
            }
        }
    }

    getTotalLayers() {
        let map_root = this.getMapRoot();
        let layer = 0;
        while (true) {
            let xhttp = new XMLHttpRequest();
            xhttp.open("GET", map_root + "base" + suffix + "/layer" + layer + ".dzi", false);
            try {
                xhttp.send(null);
            } catch (error) {
                return layer;
            }
            if (xhttp.status != 200) {
                return layer;
            }
            layer++;
        }
    }

    loadMapInfo() {
        let xhttp = new XMLHttpRequest();
        xhttp.open("GET", this.getMapRoot() + "base" + suffix + "/map_info.json", false);
        try {
            xhttp.send(null);
        } catch (error) {
        } 
        if (xhttp.status === 200) {
            let info = JSON.parse(xhttp.responseText);
            this.x0 = info.x0;
            this.y0 = info.y0;
            this.w = info.w;
            this.h = info.h;
            this.sqr = info.sqr;
            this.cell_rects = info.cell_rects;
        }
    }

    init() {
        this.layers = this.getTotalLayers();
        this.tiles = Array(this.layers).fill(0);
        this.loadMapInfo();
        for (let type of ['zombie', 'foraging', 'room', 'objects']) {
            this.overlays[type] = 0;
        }
    }

    setBaseLayer(layer) {
        let start = 0;
        if (this.is_base) {
            start = 1;
        }
        for (let i = start; i < this.layers ; i++) {
            if (i > layer) {
                this._unload('base', i);
            }
        }
        for (let i = start; i <= layer && i < this.layers ; i++) {
            this._load('base', i);
        }
    }

    setOverlayLayer(overlay, layer) {
        for (let type of ['zombie', 'foraging', 'room', 'objects']) {
            if (overlay[type]) {
                if (!['zombie', 'foraging'].includes(type)) {
                    if (layer != this.overlay_layer) {
                        this._unload(type, layer);
                    }
                }
                this._load(type, layer);
            } else {
                this._unload(type, layer);
            }
        }
        this.overlay_layer = layer;
    }

    destroy() {
        this.setBaseLayer(-1);
        this.setOverlayLayer({}, 0);
    }
}

// order layered maps
function positionItem(item, name, layer) {
    //let cur = viewer.world.getIndexOfItem(item);
    let pos = 0;
    for (let i = 0; i < base_map.tiles.length; i++ ) {
        if (name == '' && layer == i) {
            viewer.world.setItemIndex(item, pos);
            return;
        }
        if (![0, null, 'delete'].includes(base_map.tiles[i])) {
            pos++;
        }
    }
    for (let i = 0; i < mod_maps.length; i++ ) {
        for (let j = 0; j < mod_maps[i].tiles.length; j++ ) {
            if (name == mod_maps[i].name && layer == j) {
                viewer.world.setItemIndex(item, pos);
                return;
            }
            if (![0, null, 'delete'].includes(mod_maps[i].tiles[j])) {
                pos++;
            }
        }
    }
}

function positionAll() {
    let pos = 0;
    for (let i = 0; i < base_map.tiles.length; i++ ) {
        if (![0, null, 'delete'].includes(base_map.tiles[i])) {
            viewer.world.setItemIndex(base_map.tiles[i], pos);
            pos++;
        }
    }
    for (let i = 0; i < mod_maps.length; i++ ) {
        for (let j = 0; j < mod_maps[i].tiles.length; j++ ) {
            if (![0, null, 'delete'].includes(mod_maps[i].tiles[j])) {
                viewer.world.setItemIndex(mod_maps[i].tiles[j], pos);
                pos++;
            }
        }
    }
}

var base_map = 0;
var mod_maps = [];
var overlays = {};
var currentLayer = 0;

var mapui = 0;
var grid = 0;
var trimmer = 0;
var save_path = "";
var saved_blocks = new Set();
var saved_cells = {};
var selected_blocks = new Set();
var selected_cells = {};
var cell_font = '12pt bold monospace';
var block_font = '12pt monospace';

var min_step_cell = 8;
var min_step_block = 8;
var rectLevel = 0;
var rectX1 = 0;
var rectY1 = 0;
var rectX2 = 0;
var rectY2 = 0;
var grid2key;

var UI_HTML = {
    foraging: `
    Foraging Legends:
    <div class="legend" style="background-color:#fff"></div>Road
    <div class="legend" style="background-color:#00f"></div>Urban Area
    <div class="legend" style="background-color:#0ff"></div>Trailer Park
    <div class="legend" style="background-color:#ff0"></div>Vegitation
    <div class="legend" style="background-color:#0f0"></div>Forest
    <div class="legend" style="background-color:#080"></div>Deep Forest
    <div class="legend" style="background-color:#f0f"></div>Farmland
    <div class="legend" style="background-color:#f00"></div>Farm`,

    objects: `
    Objects Legends:
    <div class="legend" style="border-color:#f00; border-width: 3px;"></div>Zombies Type
    <div class="legend" style="border-color:#00f; border-width: 3px;"></div>Car Spawn
    <div class="legend" style="border-color:#ff0; border-width: 3px;"></div>Zone Story`,

    trimmer: `
    <b>[Save File Trimmer]</b> Legends:
    <div class="legend" style="background-color:#0f0"></div>Saved Area
    <div class="legend" style="background-color:#00f"></div>Partial Saved Area
    <div class="legend" style="background-color:#f00"></div>Selected
    <div class="legend" style="background-color:#ff0"></div>Partial Selected
    <a id="trimmer_help_btn" href="" class="text-right" onclick="return toggleTrimmerHelp();">Show Help</a>
    <div id="trimmer_help"></div>
    <b>Select Save:</b>
    <select id="save_selector" onchange="onSaveSelect()">
        <option value="">(Select Save Slot)</option>
    </select>
    <button type="button" onclick="doRefresh()">Refresh Save List</button>
    <input type="checkbox" id="vehicle" checked>
    <label for="vehicle"> Remove Vehicles </label>
    <button type="button" onclick="doDelete()">Delete Selected Area</button>
    <div id="trimmer_output" style="display: inline-block"></div>
    <button class="text-right" type="button" onclick="openExplorer()">Browse Folder</button>`,
    
    trimmer_help: `
    <b>Instructions</b><br/>
    <b>Step 1</b> Select save slot.<br/>
    <b>Step 2</b> Select unwanted area.<br/>
    <b>Step 3</b> Delete selected area.<br/>
    <p>
    <b>How to select area</b><br/>
    <b>Click</b>: select/unselect a single grid.<br/>
    <b>Shift+Click</b>: select/unselect all area in a yellow grid.<br/>
    <b>Shift+Drag</b> Flip selection of a rectangle area.
    </p>`,

    map: `
    <select id="map_selector" onchange="onMapSelect()">
        <option value="">(Select Mod Map to Load)</option>
    </select>
    <b>Loaded maps:</b>
    <div id="map_list" style="display: inline-block"></div>`
}

function changeView() {
    if (map_type == "top") {
        map_type = 'iso';
    } else {
        map_type = 'top';
    }
    viewer.destroy();
    let map_names = [];
    for (let i = 0; i < mod_maps.length; i++) {
        map_names.push(mod_maps[i].name);
    }
    let setup_maps = function () {
        for (let i = 0; i < map_names.length; i++) {
            addMap(map_names[i]);
        }
    }
    init(setup_maps);

    return false;
}

function init_mapui() {
    let xhttp = new XMLHttpRequest();
    xhttp.open("GET", "./mod_maps/map_list.json", false);
    try {
        xhttp.send(null);
    } catch (error) {
    } 
    if (xhttp.status === 200) {
        let s = document.getElementById('map_selector')
        let map_names = JSON.parse(xhttp.responseText);
        for (let i = 0; i < map_names.length; i++) {
            let o = document.createElement("option");
            o.value = map_names[i];
            o.text = map_names[i];
            s.appendChild(o);
        }
    }
}

function updateClip() {
    base_map.setClipFromOverlayMaps(mod_maps);
    for (let i = 0; i < mod_maps.length; i++) {
        mod_maps[i].setClipFromOverlayMaps(mod_maps.slice(i + 1));
    }
}

function removeMap(name) {
    let pos = 0;
    for (pos = 0; pos < mod_maps.length; pos++) {
        if (name == mod_maps[pos].name) {
            break;
        }
    }
    if (pos < mod_maps.length) {
        mod_maps[pos].destroy();
        mod_maps.splice(pos, 1);
        if (mod_maps.length == 0) {
            document.getElementById("map_btn").classList.remove('active');
        }
        updateMapUI();
        updateClip();
    }
}

function addMap(name) {
    if (name != '') {
        let pos = 0;
        for (pos = 0; pos < mod_maps.length; pos++) {
            if (name === mod_maps[pos].name) {
                break;
            }
        }
        if (pos >= mod_maps.length) {
            mod_maps.push(new Map(name));
            if (mod_maps.length == 1) {
                document.getElementById("map_btn").classList.add('active');
            }
            updateMapUI();
            updateClip();
            updateMaps(currentLayer);
        }
    }
}

function onMapSelect() {
    if (mapui) {
        let s = document.getElementById('map_selector');
        addMap(s.value);
        s.value = '';
    }
}

function initUI() {
    if (map_type == "top") {
        for (let e of document.getElementsByClassName('iso')) {
            e.style.display = "none";
        }
        document.getElementById('change_view').innerHTML = "Isometric View";
        document.title = "PZ map (Top View)";
    } else {
        for (let e of document.getElementsByClassName('iso')) {
            e.style.display = "";
        }
        document.getElementById('change_view').innerHTML = "Top View";
        document.title = "PZ map";
    }
    let s = document.getElementById('layer_selector')
    for (let i = s.options.length - 1; i >= 0; i--) {
        s.remove(i);
    }
    for (let i = 0; i < base_map.layers; i++) {
        let o = document.createElement("option");
        o.value = i;
        o.text = 'Layer ' + i;
        s.appendChild(o);
    }
    for (let type of ['zombie', 'foraging', 'room', 'objects', 'grid', 'map']) {
        let ui = document.getElementById(type + '_ui');
        if (ui) {
            ui.innerHTML = "";
        }
        let btn = document.getElementById(type + '_btn');
        if (btn) {
            btn.classList.remove('active');
        }
    }

    setOutput('main_output', 'green', '');
    document.body.style.background = 'black';
}

function init(callback=null) {
    if (map_type == "top") {
        suffix = "_top";
    } else {
        suffix = "";
    }

    base_map = new Map('', true);
    mod_maps = [];
    overlays = {};
    currentLayer = 0;
    viewer;

    mapui = 0;
    grid = 0;
    trimmer = 0;
    save_path = "";
    saved_blocks = new Set();
    saved_cells = {};
    selected_blocks = new Set();
    selected_cells = {};
    cell_font = '12pt bold monospace';
    block_font = '12pt monospace';
    min_step_cell = 8;
    min_step_block = 8;
    rectLevel = 0;
    rectX1 = 0;
    rectY1 = 0;
    rectX2 = 0;
    rectY2 = 0;
    initUI();
    updateClip();

    viewer = OpenSeadragon({
        element: document.getElementById("map_div"),
        tileSources:  "base" + suffix + "/layer0.dzi",
        homeFillsViewer: true,
        showZoomControl: true,
        constrainDuringPan: true,
        visibilityRatio: 0.5,
        prefixUrl: "openseadragon/images/",
        navigatorBackground: 'black',
        minZoomImageRatio: 0.5,
        maxZoomPixelRatio: map_type == "top" ? 12 : 2
    });

    viewer.addHandler('add-item-failed', function(event) {
        let info = '<b>Map not loaded. Use "run_server.bat" to start the viewer.</b>';
        if (window.location.protocol == 'http:' || window.location.protocol == 'https:') {
            let type_str = (map_type == "top") ? "top" : "isometric";
            info = '<b>Failed to load ' + type_str + ' view map.</b>';
        }
        setOutput('main_output', 'red', info);
        document.body.style.background = 'white';
    })

    viewer.addHandler('update-viewport', function() {
        if (grid == 0 && trimmer == 0) {
            return;
        }
        let ctx = viewer.drawer.context;
        let [c00, step_cell, step_block] = getCanvasOriginAndStep();

        let [cell, block, cell_text_offset, block_text_offset] = getGridLevel(ctx, step_cell, step_block);

        if (trimmer) {
            drawEditState(ctx, c00, block ? step_block : step_cell, block);
        }
        if (block) {
            ctx.strokeStyle = 'lime';
            drawGrid(ctx, c00, step_block, 1);
        }
        if (block_text_offset) {
            ctx.fillStyle = 'lime';
            ctx.font = block_font;
            drawCoord(ctx, c00, step_block, block_text_offset);
        }
        if (cell) {
            ctx.strokeStyle = 'yellow';
            drawGrid(ctx, c00, step_cell, cell);
        }
        if (cell_text_offset) {
            ctx.fillStyle = 'yellow';
            ctx.font = cell_font;
            drawCoord(ctx, c00, step_cell, cell_text_offset);
        }
    })

    viewer.addHandler('canvas-press', function(event) {
        if (trimmer && event.originalEvent.shiftKey) {
            let ctx = viewer.drawer.context;
            let x = event.position.x * window.devicePixelRatio;
            let y = event.position.y * window.devicePixelRatio;
            let [c00, step_cell, step_block] = getCanvasOriginAndStep();
            let [cell, block, cto, bto] = getGridLevel(ctx, step_cell, step_block);
            if (block) {
                rectLevel = 'block';
                [rectX1, rectY1] = getGridXY(c00, step_block, x, y);
            } else if (cell) {
                rectLevel = 'cell';
                [rectX1, rectY1] = getGridXY(c00, step_cell, x, y);
            }
            rectX2 = rectX1;
            rectY2 = rectY1;

            viewer.forceRedraw();
            viewer.raiseEvent('update-viewport', {});
            event.preventDefaultAction = true;
        }
    })

    viewer.addHandler('canvas-drag', function(event) {
        if (trimmer && rectLevel) {
            let ctx = viewer.drawer.context;
            let x = event.position.x * window.devicePixelRatio;
            let y = event.position.y * window.devicePixelRatio;
            let [c00, step_cell, step_block] = getCanvasOriginAndStep();
            let [cell, block, cto, bto] = getGridLevel(ctx, step_cell, step_block);
            if (rectLevel == 'block') {
                [rectX2, rectY2] = getGridXY(c00, step_block, x, y);
            } else if (rectLevel == 'cell') {
                [rectX2, rectY2] = getGridXY(c00, step_cell, x, y);
            }
            if (!event.originalEvent.shiftKey) {
                rectLevel = 0;
            }

            viewer.forceRedraw();
            viewer.raiseEvent('update-viewport', {});
            event.preventDefaultAction = true;
        }
    })

    viewer.addHandler('canvas-release', function(event) {
        if (rectLevel) {
            if (trimmer && event.originalEvent.shiftKey) {
                if (rectX1 != rectX2 || rectY1 != rectY2) {
                    let ctx = viewer.drawer.context;
                    let x = event.position.x * window.devicePixelRatio;
                    let y = event.position.y * window.devicePixelRatio;
                    let [c00, step_cell, step_block] = getCanvasOriginAndStep();
                    let [cell, block, cto, bto] = getGridLevel(ctx, step_cell, step_block);
                    for (let i = Math.min(rectX1, rectX2); i <= Math.max(rectX1, rectX2); i++) {
                        for (let j = Math.min(rectY1, rectY2); j <= Math.max(rectY1, rectY2); j++) {
                            if (rectLevel == 'block') {
                                flipBlock(i, j);
                            } else if (rectLevel == 'cell') {
                                flipCell(i, j);
                            }
                        }
                    }
                }

                rectLevel = 0;
                viewer.forceRedraw();
                viewer.raiseEvent('update-viewport', {});
                event.preventDefaultAction = true;
            }
            rectLevel = 0;
        }
    })

    viewer.addHandler('canvas-click', function(event) {
        if (event.quick && trimmer != 0) {
            let ctx = viewer.drawer.context;
            let x = event.position.x * window.devicePixelRatio;
            let y = event.position.y * window.devicePixelRatio;
            let [c00, step_cell, step_block] = getCanvasOriginAndStep();
            let [cell, block, cto, bto] = getGridLevel(ctx, step_cell, step_block);
            if (event.originalEvent.shiftKey) {
                block = 0;
            }
            if (block) {
                let [bx, by] = getGridXY(c00, step_block, x, y);
                flipBlock(bx, by);
            } else if (cell) {
                let [bx, by] = getGridXY(c00, step_cell, x, y);
                flipCell(bx, by);
            }
            viewer.forceRedraw();
            viewer.raiseEvent('update-viewport', {});
            event.preventDefaultAction = true;
        }
    })

    if (map_type == "top") {
        viewer.drawer.context.imageSmoothingEnabled = false;
        grid2key = grid2keyTop;
    } else {
        grid2key = grid2keyIso;
    }
    let success_callback = function (retry) {
        let img = viewer.world.getItemAt(0);
        if (img && img.getFullyLoaded()) {
            base_map.tiles[0] = img;
            if (callback) {
                callback();
            }
        } else {
            setTimeout(retry, 1, retry);
        }
    }
    success_callback(success_callback);
}

function shiftClipList(clip_list, layer=null) {
    let clip_list_shift = [];
    if (layer == null) {
        layer = currentLayer;
    }
    let shift = -192 * layer;
    for (let i = 0; i < clip_list.length; i++) {
        let points = [];
        for (let j = 0; j < clip_list[i].length; j++) {
            points.push({x: clip_list[i][j].x, y: clip_list[i][j].y + shift})
        }
        clip_list_shift.push(points);
    }
    return clip_list_shift;
}

function rectIntersect(r1, r2) {
    let [x1, y1, w1, h1] = r1;
    let [x2, y2, w2, h2] = r2;
    return (x1 < x2 + w2) && (x2 < x1 + w1) && (y1 < y2 + h2) && (y2 < y1 + h1);
}

function setOutput(id, color, text, timeout=0) {
    let output = document.getElementById(id);
    if (output) {
        output.style.color = color;
        output.innerHTML = text;
    }
    if (timeout > 0) {
       setTimeout(setOutput, timeout, id, color, '', 0); 
    }
}

function grid2keyTop(gx, gy) {
    return [gx, gy];
}

function grid2keyIso(gx, gy) {
    return [(gx + gy) / 2, (gy - gx) / 2];
}

function block2cell(bkey) {
    let [x, y] = bkey.split(',');
    return Math.floor(x / 30) + ',' + Math.floor(y / 30);
}

function openExplorer() {
    let xhttp = new XMLHttpRequest();
    xhttp.open("GET", "./browse", false);
    try {
        xhttp.send(null);
    } catch (error) {
    } 
    if (xhttp.status === 200) {
        setOutput('trimmer_output', 'green', '<b>File browser launched</b>', 3000);
    } else {
        setOutput('trimmer_output', 'red', '<b>Failed opening file browser, error code:' + xhttp.status + '</b>', 5000);
    }

}

function doDelete() {
    if (trimmer) {
        if (selected_blocks.size > 0) {
            deleteSave(save_path);
        } else {
            setOutput('trimmer_output', 'red', '<b>Nothing selected</b>', 3000);
        }
    }
}

function deleteSave(path) {
    let xhttp = new XMLHttpRequest();
    xhttp.open("POST", "./delete/" + path, false);
    xhttp.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    let cells = [];
    let cells_set = new Set();
    let blocks = [];
    let count = 0;
    for (const [key, value] of Object.entries(selected_cells)) {
        if (value == saved_cells[key]) {
            count += value;
            cells.push(key);
            cells_set.add(key);
        }
    }
    for (let it = selected_blocks.values(), key = null; key = it.next().value; ) {
        if (!cells_set.has(block2cell(key))) {
            count++;
            blocks.push(key);
        }
    }
    
    let info = 'Are you sure to delete ' + count + ' block(s)?\n\n';
    let cell_info = cells.join(';');
    if (cells.length > 20) {
        cell_info = cells.slice(0,20).join(';') + ';...';
    }
    let block_info = blocks.join(';');
    if (blocks.length > 20) {
        block_info = blocks.slice(0,20).join(';') + ';...';
    }
    info += 'Details:\n'
    if (cell_info) {
        info += 'Cell (yellow grid(s)): ' + cell_info + '\n';
    }
    if (block_info) {
        info += 'Block (green grid(s)): ' + block_info + '\n';
    }
    if (!confirm(info)) {
        setOutput('trimmer_output', 'red', '<b>Trim canceled</b>', 3000);
        return;
    }
    let req = "cells=" + cells.join(';') + "&blocks=" + blocks.join(';');
    if (document.getElementById('vehicle').checked) {
        req += '&vehicles=1';
    }
    try {
        xhttp.send(req);
    } catch (error) {
    } 
    if (xhttp.status === 200) {
        setOutput('trimmer_output', 'green', '<b>Trim success</b>', 3000);
    } else {
        setOutput('trimmer_output', 'red', '<b>Trim failed, error code:' + xhttp.status + '</b>', 5000);
    }
    loadSave(path);
}

function clearSelection() {
    saved_cells = {};
    saved_blocks.clear();
    selected_cells = {};
    selected_blocks.clear();
}

function onSaveSelect() {
    if (trimmer) {
        save_path = document.getElementById('save_selector').value;
        loadSave(save_path);
    }
}

function loadSave(path) {
    if (trimmer) {
        clearSelection();
        if (path) {
            let xhttp = new XMLHttpRequest();
            xhttp.open("GET", "./load/" + path, false);
            try {
                xhttp.send(null);
            } catch (error) {
            } 
            if (xhttp.status === 200) {
                let keys = xhttp.responseText.split(';');
                for (let i = 0; i < keys.length; i++) {
                    let ckey = block2cell(keys[i]);
                    if (saved_cells[ckey] == undefined) {
                        saved_cells[ckey] = 0;
                    }
                    saved_cells[ckey] += 1;
                    saved_blocks.add(keys[i]);
                }
            } else {
                let info = '<b>Failed to load save [' + path + '], error code:' + xhttp.status + '</b>';
                setOutput('trimmer_output', 'red', info, 5000);
            }
        }
        viewer.forceRedraw();
        viewer.raiseEvent('update-viewport', {});
    }
}

function doRefresh() {
    if (trimmer) {
        listSave();
    }
}

function listSave() {
    if (trimmer) {
        clearSelection();
        let s = document.getElementById('save_selector')
        for (let i = s.options.length - 1; i > 0; i--) {
            s.remove(i);
        }

        let xhttp = new XMLHttpRequest();
        xhttp.open("GET", "./list_save", false);
        try {
            xhttp.send(null);
        } catch (error) {
        } 
        if (xhttp.status === 200) {
            let saves = JSON.parse(xhttp.responseText);
            for (let i = 0; i < saves.length; i++) {
                let o = document.createElement("option");
                o.value = saves[i];
                o.text = saves[i];
                s.appendChild(o);
                if (saves[i] == save_path) {
                    s.value = save_path;
                }
            }
            save_path = s.value;
            if (save_path) {
                loadSave(save_path);
            }
            setOutput('trimmer_output', 'green', '<b>Save list loaded</b>', 3000);
        } else {
            let info = '<b>Failed to list save, error code:' + xhttp.status + '</b>';
            if (xhttp.status == 0) {
                info = '<b>[Save File Trimmer] require server mode to function. Use "run_server.bat" to start the viewer.</b>';
            }
            setOutput('trimmer_output', 'red', info, 5000);
        }
        viewer.forceRedraw();
        viewer.raiseEvent('update-viewport', {});
    }
}

function textSize(ctx, text) {
    let m = ctx.measureText('-01234,56789');
    let ascent = m.actualBoundingBoxAscent;
    let descent = m.actualBoundingBoxDescent;
    let width = ctx.measureText(text).width;
    return [width, ascent, descent];
}

function* inScreenCoords(ctx, c00, step, border) {
    let w = ctx.canvas.width;
    let h = ctx.canvas.height;
    let step_x = step;
    let step_y = step;
    let y_start = 0;
    let y_inc = 1;
    if (map_type != "top") {
        step_x = step / 2;
        step_y = step / 4;
        y_inc = 2;
    }
    yield [step_x, step_y];

    let gx0 = -Math.floor(c00.x / step_x) - border;
    let cx0 = c00.x + (gx0 * step_x);
    let gy0 = -Math.floor(c00.y / step_y) - border;
    let cy0 = c00.y + (gy0 * step_y);
    let dx0 = gx0 + gy0;
    let dy0 = gy0 - gx0;

    for (let x = 0; x <= w / step_x + border * 2 - 1; x++) {
        if (map_type != "top") {
            y_start = (dx0 + x) % 2;
        }
        for (let y = y_start; y <= h / step_y + border * 2 - 1; y+=y_inc) {
            let gx = gx0 + x;
            let gy = gy0 + y;
            let [kx, ky] = grid2key(gx, gy);
            yield [gx, gy, kx, ky];
        }
    }
}

function drawCoord(ctx, c00, step, yoffset) {
    let coords = inScreenCoords(ctx, c00, step, 1);
    let [step_x, step_y] = coords.next().value;
    let xoffset = 4;
    ctx.setTransform(1, 0, 0, 1, c00.x, c00.y);
    for (let [gx, gy, kx, ky] of coords) {
        let cx = gx * step_x;
        let cy = gy * step_y;
        let text = makeKey(kx, ky);
        if (map_type != "top") {
            xoffset = - ctx.measureText(text).width / 2;
        }
        ctx.fillText(text, cx + xoffset, cy + yoffset);

    }
    ctx.setTransform();
}

function drawEditState(ctx, c00, step, is_block) {
    let coords = inScreenCoords(ctx, c00, step, 2);
    let [step_x, step_y] = coords.next().value;
    if (map_type == "top") {
        ctx.setTransform(1, 0, 0, 1, c00.x, c00.y);
    } else {
        ctx.setTransform(0.5,0.25, -0.5 ,0.25, c00.x, c00.y);
    }
    let color = 0;
    for (let [gx, gy, kx, ky] of coords) {
        let key = makeKey(kx, ky);
        if ((is_block && selected_blocks.has(key)) ||
            (!is_block && selected_cells[key] > 0 && selected_cells[key] == saved_cells[key])) {
            color = 'rgba(255,0,0,0.5)'; // full selected
        } else if (!is_block && selected_cells[key] > 0) {
            color = 'rgba(255,255,0,0.5)'; // partial selected cell
        } else if ((is_block && saved_blocks.has(key)) ||
                   (!is_block && saved_cells[key] == 900)) {
            color = 'rgba(0,255,0,0.5)'; // full saved
        } else if (!is_block && saved_cells[key] > 0) {
            color = 'rgba(0,0,255,0.5)'; // partial saved cell
        } else {
            color = 0;
        }
        if (color) {
            ctx.fillStyle = color;
            ctx.fillRect(kx * step, ky * step, step, step);
        }
    }
    // drag selecting area
    if (rectLevel) {
        let scale = 1.0;
        if (rectLevel == 'cell' && is_block) {
            scale = 30;
        }
        if (rectLevel == 'block' && !is_block) {
            scale = 1.0 / 30;
        }
        let x = Math.min(rectX1, rectX2);
        let y = Math.min(rectY1, rectY2);
        let xs = Math.abs(rectX1 - rectX2) + 1;
        let ys = Math.abs(rectY1 - rectY2) + 1;

        ctx.fillStyle = 'rgba(255,255,255,0.5)'; //white
        ctx.fillRect(x * step * scale, y * step * scale, xs * step * scale, ys * step * scale);
    }

    ctx.setTransform();
}

function drawGrid(ctx, c00, step, line_width) {
    ctx.lineWidth = line_width;
    let w = ctx.canvas.width;
    let h = ctx.canvas.height;
    let x1 = c00.x
    let y1 = c00.y
    let max_w = w;
    let min_h = 0;
    let x_shift = 0;
    let y_shift = 0;
    let y_step = step;
    if (map_type != "top") {
        x1 += 2 * c00.y;
        y1 -= c00.x / 2;
        max_w += 2 * h;
        min_h -= w / 2;
        x_shift = -2 * h;
        y_shift = w / 2;
        y_step = step / 2;
    }
    ctx.beginPath();
    x1 -= Math.floor(x1 / step) * step;
    while (x1 <= max_w) {
        ctx.moveTo(x1, 0);
        ctx.lineTo(x1 + x_shift, h);
        x1 += step;
    }
    y1 += Math.ceil((h - y1) / step) * step;
    while (y1 >= min_h) {
        ctx.moveTo(0, y1);
        ctx.lineTo(w, y1 + y_shift);
        y1 -= y_step;
    }
    ctx.stroke();
}

function getGridXY(c00, step, x, y) {
    let gx = 0;
    let gy = 0;
    if (map_type == "top") {
        gx = Math.floor((x - c00.x)/step);
        gy = Math.floor((y - c00.y)/step);
    } else {
        let cxx0 = c00.x + 2 * (c00.y - y);
        let cxy0 = c00.x - 2 * (c00.y - y);
        gx = Math.floor((x - cxx0)/step);
        gy = Math.floor((cxy0 - x)/step);
    }
    return [gx, gy];
}

function makeKey(x, y) {
    return x + ',' + y;
}

function getCanvasOriginAndStep() {
    let zm = viewer.viewport.getZoom(true);
    zm = viewer.world.getItemAt(0).viewportToImageZoom(zm);
    zm *= window.devicePixelRatio;
    let yshift = (map_type == "top" ? 0 : 192 * currentLayer);
    let vp00 = viewer.world.getItemAt(0).imageToViewportCoordinates(base_map.x0, base_map.y0 - yshift);
    let c00 = viewer.viewport.pixelFromPoint(vp00, true);
    c00.x *= window.devicePixelRatio;
    c00.y *= window.devicePixelRatio;

    let step_cell = base_map.sqr * 300 * zm;
    let step_block = base_map.sqr * 10 * zm;

    return [c00, step_cell, step_block];
}

function getGridLevel(ctx, step_cell, step_block) {
    ctx.font = cell_font;
    let [cell_width, cell_ascent, cell_descent] = textSize(ctx, '-00,-00');
    let cell_height = cell_ascent + cell_descent;
    let cell_text_offset = 0;
    let block_text_offset = 0;
    let cell = 0;
    let block = 0;
    if (step_cell >= min_step_cell * window.devicePixelRatio) {
        cell = 1;
    }
    if (step_block >= min_step_block * window.devicePixelRatio) {
        block = 1;
    }
    let min_step_cell_text = 0;
    if (map_type == "top") {
        min_step_cell_text = 8 + Math.max(cell_width, cell_height);
    } else {
        min_step_cell_text = 8 + cell_width + 2 * cell_height;
    }
    if (step_cell >= min_step_cell_text) {
        cell = 3;
        let [block_width, block_ascent, block_descent] = textSize(ctx, '-0000,-0000');
        let block_height = block_ascent + block_descent;
        let min_step_block_text = 0;
        if (map_type == "top") {
            cell_text_offset = 4 + cell_ascent;
            min_step_block_text = 8 + Math.max(block_width, 2 + block_height + cell_height);
        } else {
            cell_text_offset = 2 + cell_width / 4 + cell_ascent;
            if (block_width > cell_width) {
                min_step_block_text = 8 + block_width + 2 * (block_height + Math.max(0, cell_height - (block_width - cell_width) / 4));
            } else {
                min_step_block_text = 8 + cell_width + 2 * (cell_height + Math.max(0, block_height - (cell_width - block_width) / 4));
            }
        }
        if (step_block >= min_step_block_text) {
            block_text_offset = cell_text_offset + cell_descent + 2 + block_ascent;
        }
    } 
    return [cell, block, cell_text_offset, block_text_offset];
}

function flipBlock(x, y) {
    let key = makeKey(x, y);
    if (saved_blocks.has(key)) {
        let ckey = makeKey(Math.floor(x/30), Math.floor(y/30));
        if (selected_blocks.has(key)) {
            selected_blocks.delete(key);
            selected_cells[ckey] -= 1;
            if (selected_cells[ckey] == 0) {
                delete selected_cells[ckey];
            }
        } else {
            selected_blocks.add(key);
            if ( selected_cells[ckey] == undefined) {
                selected_cells[ckey] = 0;
            }
            selected_cells[ckey] += 1;
        }
    }
}

function flipCell(x, y) {
    let key = makeKey(x, y);
    if (saved_cells[key] != undefined) {
        if (selected_cells[key] == undefined || selected_cells[key] < saved_cells[key]) {
            selected_cells[key] = saved_cells[key];
            for (let i = 0; i < 30; i++) {
                for (let j = 0; j < 30; j++) {
                    let bkey = makeKey(x * 30 + i, y * 30 + j);
                    if (saved_blocks.has(bkey)) {
                        selected_blocks.add(bkey);
                    }
                }
            }
        } else {
            delete selected_cells[key];
            for (let i = 0; i < 30; i++) {
                for (let j = 0; j < 30; j++) {
                    let bkey = makeKey(x * 30 + i, y * 30 + j);
                    if (selected_blocks.has(bkey)) {
                        selected_blocks.delete(bkey);
                    }
                }
            }
        }
    }
}

function toggleGrid() {
    if (grid == 0) {
        grid = 1;
        document.getElementById("grid_btn").classList.add('active');
        if (trimmer == 1) {
            viewer.forceRedraw();
        }
        viewer.raiseEvent('update-viewport', {});
    } else {
        grid = 0;
        document.getElementById("grid_btn").classList.remove('active');
        viewer.forceRedraw();
    }
}

function toggleTrimmer() {
    if (trimmer == 0) {
        trimmer = 1;
        document.getElementById("trimmer_btn").classList.add('active');
        document.getElementById("trimmer_ui").innerHTML = UI_HTML['trimmer'];
        listSave();
        if (grid == 1) {
            viewer.forceRedraw();
        }
        viewer.raiseEvent('update-viewport', {});
    } else {
        trimmer = 0;
        document.getElementById("trimmer_btn").classList.remove('active');
        document.getElementById("trimmer_ui").innerHTML = "";
        viewer.forceRedraw();
    }
}

function toggleTrimmerHelp() {
    if (trimmer) {
        let t = document.getElementById("trimmer_help");
        let ins = document.getElementById("trimmer_help_btn");
        if (t.textContent) {
            t.innerHTML = "";
            ins.innerHTML = "Show Help";
        } else {
            t.innerHTML = UI_HTML['trimmer_help'];;
            ins.innerHTML = "Hide Help";
        }
    }
    return false;
}

function toggleModMapUI() {
    if (mapui == 0) {
        mapui = 1;
        document.getElementById("map_ui").innerHTML = UI_HTML['map'];
        init_mapui();
        updateMapUI();
    } else {
        mapui = 0;
        document.getElementById("map_ui").innerHTML = "";
    }
}

function updateMapUI() {
    if (mapui) {
        d = document.getElementById("map_list");
        d.innerHTML = '';
        for (let pos = 0; pos < mod_maps.length; pos++) {
            d.innerHTML += `<button class="active" style="cursor: not-allowed"
                onclick="removeMap('${mod_maps[pos].name}')">${mod_maps[pos].name}</button>`;
        }
    }
}

function updateMaps(layer) {
    base_map.setBaseLayer(layer);
    base_map.setOverlayLayer(overlays, layer);
    for (let i = 0; i < mod_maps.length; i++) {
        mod_maps[i].setBaseLayer(layer);
        mod_maps[i].setOverlayLayer(overlays, layer);
    }
    currentLayer = layer;
}

function toggleOverlay(type) {
    overlays[type] = !overlays[type];
    if (overlays[type]) {
        document.getElementById(type + "_btn").classList.add('active');
        let ui = document.getElementById(type + "_ui");
        if (ui) {
            ui.innerHTML = UI_HTML[type];
        }
    } else {
        document.getElementById(type + "_btn").classList.remove('active');
        let ui = document.getElementById(type + "_ui");
        if (ui) {
            ui.innerHTML = "";
        }
    }
    updateMaps(currentLayer);
}

function onLayerSelect() {
    let layer = Number(document.getElementById('layer_selector').value);
    updateMaps(layer);
}

init();

