import { g } from "./globals.js";
import * as i18n from "./i18n.js";
import * as c from "./coordinates.js";
import * as util from "./util.js";
import * as ui from "./ui.js";

var ZOOM_IN_STEP = 0.25;
var ZOOM_TO_STEP = 2;
var DEFAULT_MARKER_OPTIONS = {
    id: '',
    name: '',
    desc: '',
    class_list: undefined,
    visiable_zoom_level: 0,
    passthrough: undefined,
};
var ZOOM_LEVEL_STEP_SIZE = [
    0,     // level 0, always visible
    0.25,  // level 1, single square takes 0.25 pixels
    8      // level 2, single square takes 8 pixels
];

var CURRENT = {
    level: 0,
    size: 0
}

export function zoom() {
    // canvas event
    let change = false;
    let zoom = c.getZoom(g.viewer, false);
    let step = zoom * g.base_map.sqr;
    let size = 3; // large
    if (step < 1.0) {
        size = 1; // small
    } else {
        if (step < 2.0) {
            size = 2; // mid
        }
    }
    if (CURRENT.size !== size) {
        CURRENT.size = size;
        util.changeStyle('.point', 'width', size*10 + 'px');
        util.changeStyle('.point', 'height', size*10 + 'px');
        util.changeStyle('.area-iso', 'border-width', size*8 + 'px');
        util.changeStyle('.area-top', 'border-width', size*4 + 'px');
        change = true;
    }
    let zoom_level = 1;
    while (step > ZOOM_LEVEL_STEP_SIZE[zoom_level]) {
        zoom_level += 1;
    }
    if (CURRENT.zoom_level != zoom_level) {
        // update visibility when zoom level changed
        CURRENT.zoom_level = zoom_level;
        for (let level in ZOOM_LEVEL_STEP_SIZE) {
            util.changeStyle('.zoom' + level, 'visibility', level < zoom_level ? 'visible' : 'hidden');
            util.changeStyle('.zoom' + level, 'pointer-events', level < zoom_level ? 'auto' : 'none');
            util.changeStyle('.passthrough-zoom' + level, 'visibility', level < zoom_level ? 'visible' : 'hidden');
        }
        change = true;
    }
    return change;
}

function setMarkClass(e, type, layer, cls) {
    e.className = "";
    e.classList.add('mark')
    e.classList.add(type)
    e.classList.add(type + '-' + g.map_type)
    if (layer > g.currentLayer) {
        e.classList.add('above');
        e.classList.add('above' + (layer - g.currentLayer)) - layer;
    }
    if (layer < g.currentLayer) {
        e.classList.add('below');
        e.classList.add('below' + (g.currentLayer - layer));
    }
    for (let c of cls) {
        e.classList.add(c);
    }
}

function draw(position, size, element) {
    let wrapper = element.parentElement;
    element.style.display = 'block';
    wrapper.style.left = position.x + 'px';
    wrapper.style.top = position.y + 'px';
    wrapper.style['pointer-events'] = 'none';
    if (element.classList.contains('area')) {
        let border = 8*CURRENT.size;
        if (element.classList.contains('cursor')) {
            border = 1;
        }
        if (g.map_type != 'top') {
            element.style.transform = 'matrix(0.5, 0.25, -0.5, 0.25, 0, 0)';
            border *= 2;
        }
        element.style.width = (size.x - border) + 'px';
        element.style.height = (size.y - border) + 'px';
    }
}

function overlayPoint(id, cls, title, x, y, layer) {
    let vp = c.getViewportPointBySquare(g.viewer, g.base_map, x + 0.5, y + 0.5, layer);
    let point = new OpenSeadragon.Point(vp.x, vp.y);
    let e = document.getElementById(id);
    if (e) {
        e.title = title;
        setMarkClass(e, 'point', layer, cls);
        g.viewer.updateOverlay(e, point, OpenSeadragon.Placement.CENTER);
    } else {
        e = document.createElement('div');
        e.id = id;
        e.title = title;
        setMarkClass(e, 'point', layer, cls);
        g.viewer.addOverlay(e, point, OpenSeadragon.Placement.CENTER, draw);
    }
    return e;
}

function overlayRect(id, cls, title, x, y, layer, w, h) {
    let vp = c.getViewportPointBySquare(g.viewer, g.base_map, x, y, layer);
    let step = g.viewer.world.getItemAt(0).imageToViewportCoordinates(g.base_map.sqr, 0).x;
    let rect = new OpenSeadragon.Rect(vp.x, vp.y, step*w, step*h);
    let e = document.getElementById(id);
    if (e) {
        e.title = title;
        setMarkClass(e, 'area', layer, cls);
        g.viewer.updateOverlay(e, rect, OpenSeadragon.Placement.TOP_LEFT);
    } else {
        e = document.createElement('div');
        e.id = id;
        e.title = title;
        setMarkClass(e, 'area', layer, cls);
        g.viewer.addOverlay(e, rect, OpenSeadragon.Placement.TOP_LEFT, draw);
    }
    return e;
}

function removeOverlay(id) {
    let e = document.getElementById(id);
    if (e) {
        g.viewer.removeOverlay(e);
    }
}

function getId(e) {
    let id = e.id.substring(e.id.indexOf('-',3)+1);
    return id;
}

//window.addEventListener('click', click);

class Mark {
    constructor(obj, keys) {
        this.selected = false;
        this.removed = false;
        this.backup = {};
        this.keys = Object.keys(DEFAULT_MARKER_OPTIONS).concat(keys);
        for (let key of this.keys) {
            if (obj[key] === undefined) {
                if (DEFAULT_MARKER_OPTIONS[key] !== undefined) {
                    this[key] = DEFAULT_MARKER_OPTIONS[key];
                }
            } else {
                this[key] = obj[key];
            }
        }
        this.visiable_zoom_level = Number(this.visiable_zoom_level);
        if (!Number.isInteger(this.visiable_zoom_level)) {
            this.visiable_zoom_level = 0;
        }
    }

    cls() {
        let c = [];
        if (this.selected) { c.push('selected'); }
        if (this.passthrough) {
            c.push('passthrough-zoom' + this.visiable_zoom_level);
        } else {
            c.push('zoom' + this.visiable_zoom_level);
        }
        if (this.class_list) {
            c = c.concat(this.class_list);
        }

        return c;
    }

    setSelect(flag) {
        if (this.selected !== flag) {
            this.selected = flag;
            this.updateOverlay();
        }
    }

    setRemove(flag) {
        if (this.removed !== flag) {
            this.removed = flag;
            this.updateOverlay();
        }
    }

    showOnUI() {
        ui.setMarkerUIData(this.toObject());
    }

    getBackup() {
        if (Object.keys(this.backup).length == 0) {
            this.backup = this.toObject();
        }
    }

    dropBackup() {
        this.backup = {};
    }

    restoreBackup() {
        for (let [key, value] of Object.entries(this.backup)) {
            this[key] = value;
        }
        this.updateOverlay();
    }

    toObject() {
        let o  = {type: this.constructor.name.toLowerCase()};
        for (let key of this.keys) {
            o[key] = structuredClone(this[key]);
        }
        return o;
    }

    move(obj) {
        let type = this.constructor.name.toLowerCase();
        if (is_legal[type](obj)) {
            this.getBackup();
            for (let key of this.keys) {
                if (key !== 'id') {
                    this[key] = obj[key];
                }
            }
            this.updateOverlay();
            return true;
        }
        return false;
    }

    zoomTo() {
        let [x, y] = this.center();
        let layer = Math.round(this.layer);
        let setLayer = true;
        if (!Number.isInteger(layer)) {
            layer = 0;
            setLayer = false;
        }
        let vp = c.getViewportPointBySquare(g.viewer, g.base_map, x, y, layer);
        g.viewer.viewport.panTo(vp, true).zoomTo(c.stepToZoom(ZOOM_TO_STEP), vp);
        if (setLayer) {
            return layer;
        } else {
            return null;
        }
    }
};

class Point extends Mark {
    constructor(obj) { super(obj, ['x', 'y', 'layer']); }

    updateOverlay() {
        let pid = 'mp-0-' + this.id;
        if (this.removed) {
            removeOverlay(pid);
        } else {
            let e = overlayPoint(pid, this.cls(), this.name, this.x, this.y, this.layer);
        }
    }

    start_drag() {
        this.sx = this.x;
        this.sy = this.y;
    }

    drag(x, y) {
        let obj = this.toObject();
        obj.x = this.sx + x;
        obj.y = this.sy + y;
        this.move(obj);
    }

    text() {
        return `(${this.x}, ${this.y} L ${this.layer})`;
    }

    center() {
        return [this.x, this.y];
    }
};

class Area extends Mark {
    constructor(obj) { super(obj, ['layer', 'rects']); }

    updateOverlay() {
        for (let i in this.rects) {
            let aid = 'ma-' + i + '-' + this.id;
            if (this.removed) {
                removeOverlay(aid);
            } else {
                let r = this.rects[i];
                let e = overlayRect(aid, this.cls(), this.name, r.x, r.y, this.layer, r.width, r.height);
            }
        }
    }

    start_drag(i=0) {
        if (this.rects.length <= i) {
            this.i = -1;
            return false;
        }
        this.i = i;
        this.sx = this.rects[i].x;
        this.sy = this.rects[i].y;
        this.sw = this.rects[i].width;
        this.sh = this.rects[i].height;
    }

    drag(x, y) {
        let obj = this.toObject();
        let r = this.rects[0];
        let dx = this.sx + x - r.x;
        let dy = this.sy + y - r.y;
        for (let i in obj.rects) {
            obj.rects[i].x += dx;
            obj.rects[i].y += dy;
        }
        this.move(obj);
    }

    resize(x, y) {
        if (this.rects.length <= this.i && this.i >= 0) {
            return false;
        }
        let obj = this.toObject();
        if (x < 0) {
            obj.rects[this.i].x = this.sx + x;
            obj.rects[this.i].width = this.sw - x;
        } else {
            obj.rects[this.i].x = this.sx;
            obj.rects[this.i].width = this.sw + x;
        }
        if (y < 0) {
            obj.rects[this.i].y = this.sy + y;
            obj.rects[this.i].height = this.sh - y;
        } else {
            obj.rects[this.i].y = this.sy;
            obj.rects[this.i].height = this.sh + y;
        }
        this.move(obj);
    }

    text() {
        return `(${this.rects[0].x}, ${this.rects[0].y} L ${this.layer}, ${this.rects[0].width}x${this.rects[0].height})`;
    }

    center() {
        let r = this.rects[0];
        let x = r.x + r.width/2;
        let y = r.y + r.height/2;
        return [x, y];
    }
};

var mark_cls = {
    point: Point,
    area: Area
};

function is_legal_rects(rects) {
    if (!Array.isArray(rects)) {
        return false;
    }
    for (let r of rects) {
        if (!Number.isInteger(r.x) ||
            !Number.isInteger(r.y) ||
            !Number.isInteger(r.width) ||
            !Number.isInteger(r.height) ||
            r.width <= 0 || r.height <= 0) {
            return false;
        }
    }
    return true;
}

var is_legal = {
    point: (o) => (
        typeof o.name === 'string' &&
        typeof o.desc === 'string' &&
        Number.isInteger(o.visiable_zoom_level) &&
        Number.isInteger(o.layer) &&
        Number.isInteger(o.x) &&
        Number.isInteger(o.y)),
    area: (o) => (
        typeof o.name === 'string' &&
        typeof o.desc === 'string' &&
        Number.isInteger(o.visiable_zoom_level) &&
        Number.isInteger(o.layer) &&
        is_legal_rects(o.rects))
}

export class Marker {
    markers = {};
    state = 'Idle';
    sid = 0;
    new_id = 0;
    newmark = 0;

    constructor() {
    }

    add(obj) {
        let type = obj.type;
        let id = obj.id;
        this.remove(id);
        this.markers[id] = new mark_cls[type](obj);
        this.redraw(id);
        return id;
    }

    remove(id) {
        let m = this.markers[id];
        if (m) {
            m.setRemove(true);
            delete this.markers[id];
        }
    }

    redraw(id) {
        this.markers[id].updateOverlay();
    }

    clearUI() {
        let keys = ['name', 'x', 'y', 'layer', 'width', 'height', 'desc'];
        for (let key of keys) {
            util.setValue('marker_' + key, '')
        }
        util.setChecked('marker_hide', false);
    }

    updateUI() {
        let m = 0;
        switch(this.state) {
            case 'New':
            case 'Select':
                m = this.markers[this.sid];
                if (m) {
                    m.showOnUI();
                }
                break;
            case 'Idel':
            default:
                this.clearUI();
        }
    }

    update() {
        // state
        if (this.sid) {
            let m = this.markers[this.sid];
            let cls = m.constructor.name;
            this.state = this.sid == this.new_id ? 'New' : 'Select';
            let info = i18n.T('Marker' + this.state) + ' ' + i18n.T('Marker' + cls) + ' [' + m.text() + ']';
            util.setOutput('marker_output', 'Green', info);
        } else {
            this.state = 'Idle';
            util.setOutput('marker_output', 'Green', i18n.T('MarkerIdle'));
        }
        // ui
        this.updateUI();
    }

    updateByInput(obj) {
        if (!this.sid) {
            return;
        }
        let m = this.markers[this.sid];
        if (m) {
            m.move(obj);
        }
    }

    unSelect() {
        if (this.sid) {
            let m = this.markers[this.sid];
            if (m) {
                m.setSelect(false);
                m.restoreBackup();
            }
            this.sid = 0;
        }
        if (this.new_id) {
            this.remove(this.new_id);
            this.new_id = 0;
        }
    }

    select(id) {
        if (id == this.sid) {
            return true;
        }
        this.unSelect();
        let m = this.markers[id];
        if (m) {
            m.setSelect(true);
            this.sid = id;
            return true;
        }
        return false;
    }

    redrawAll() {
        for (let id in this.markers) {
            this.markers[id].updateOverlay();
        }
    }

    createNew(obj=null, saved=false) {
        if (obj === null) {
            obj = ui.getMarkerUIData();
        }
        if (obj.invalid) {
            return false;
        }   
        if (is_legal.point(obj)) {
            obj.type = 'point';
        }
        if (is_legal.area(obj)) {
            obj.type = 'area';
        }
        if (!obj.type) {
            return false;
        }
        let uid = util.uniqueId();
        obj.id = uid;
        this.add(obj);
        if (!saved) {
            if(this.select(uid)) {
                this.new_id = uid;
            }
        }
        this.update();
        return true;
    }

    click(event) {
        let e = event.originalTarget;
        if (e && e.classList.contains('mark')) {
            this.selectElement(e);
        } else {
            if (event.originalEvent.shiftKey) {
                let [x, y] = c.getSquare(event);
                let obj = {x: x, y: y, layer: g.currentLayer}; // point
                this.createNew(Object.assign(obj, DEFAULT_MARKER_OPTIONS));
            }
        }
        return null;
    }

    press(event) {
        let e = event.originalEvent.target;
        let [x, y] = c.getSquare(event);
        let s = {x:x, y:y};
        if (e && e.classList.contains('mark')) {
            this.selectElement(e);
            let m = this.markers[this.sid];
            m.start_drag();
            this.dragging = 'move';
            this.start = s;
            return true;
        } else {
            if (event.originalEvent.shiftKey) {
                let obj = {
                    rects: [{x: x, y: y, width: 1, height: 1}],
                    layer: g.currentLayer
                }; // area
                this.createNew(Object.assign(obj, DEFAULT_MARKER_OPTIONS));
                let m = this.markers[this.sid];
                m.start_drag();
                m.setRemove(true);
                this.dragging = 'resize';
                this.start = s;
                return true;
            }
        }
        return false;
    }

    drag(event) {
        if (!this.dragging) {
            return false;
        }
        let [x, y] = c.getSquare(event);
        if (this.dragging == 'move') {
            let m = this.markers[this.sid];
            if (m) {
                m.drag(x - this.start.x, y - this.start.y);
            }
            this.update();
            return true;
        }
        if (this.dragging == 'resize') {
            let m = this.markers[this.sid];
            if (m) {
                m.setRemove(false);
                m.resize(x - this.start.x, y - this.start.y);
            }
            this.update();
            return true;
        }
        return false;
    }

    release(event) {
        if (this.dragging) {
            if (this.dragging == 'resize') {
                let m = this.markers[this.sid];
                if (m.removed) {
                    this.unSelect();
                    this.update();
                } else {
                    m.showOnUI();
                }
            }
            this.dragging = 0;
            return true;
        }
        return false;
    }

    // ui event
    selectElement(e) {
        let id = getId(e);
        this.select(id);
        this.update();
    }

    focusSelected() {
        if (!this.sid) {
            this.createNew();
        }
        if (this.sid) {
            let m = this.markers[this.sid];
            if (m) {
                return m.zoomTo();
            }
        }
        return null;
    }

    save() {
        if (this.sid) { // selecting & new
            let m = this.markers[this.sid];
            if (m) {
                m.dropBackup();
            }
            this.new_id = 0;
        } else { // no selecting, try use ui data
            this.createNew(null, true);
        }
        this.unSelect();
        this.update();
    }

    removeSelected() {
        let id = this.sid;
        this.unSelect();
        this.remove(id);
        this.update();
    }

    removeAll() {
        this.unSelect();
        let keys = Object.keys(this.markers);
        for (let id of keys) {
            this.remove(id);
            this.unSelect();
            this.update();
        }
        this.update();
    }

    Input(e) {
        let obj = ui.getMarkerUIData();
        if (!obj.invalid) {
            this.updateByInput(obj);
        }
    }

    load(obj) {
        if (!Array.isArray(obj)) {
            return;
        }
        for (let o of obj) {
            if (!util.isObject(o)) {
                continue;
            }
            if (typeof o.id !== 'string') {
                continue;
            }

            if (o.type === 'point' && is_legal.point(o)) {
                this.add(o);
            }

            if (o.type === 'area' && is_legal.area(o)) {
                this.add(o);
            }
        }
    }

    loadDefault() {
        let path = './pzmap/i18n/marks_' + i18n.getLang() +'.json';
        let p = window.fetch(path).then((r)=>r.json()).catch((e)=> {
            util.setOutput('marker_output', 'Red', i18n.T('MarkerLoadDefaultFail', {lang: i18n.getLang()}));
            let path_en = './pzmap/i18n/marks_en.json';
            return window.fetch(path_en).then((r)=>r.json()).catch((e)=> {
                util.setOutput('marker_output', 'Red', i18n.T('MarkerLoadDefaultFail', {lang: 'en'}));
                return Promise.resolve([])
            });
        });
        return p.then((obj) => {this.load(obj); return Promise.resolve(true);});

    }

    Import() {
        util.upload().then((data) => {
            if (data) {
                let json = util.parseJson(data);
                if (json) {
                    this.load(json);
                }
            }
        });
    };

    Export() {
        this.unSelect();
        this.update();
        let data = [];
        for (let id in this.markers) {
            let m = this.markers[id];
            data.push(m.toObject());
        }
        let s = JSON.stringify(data, null, '  ');
        util.download('marks.json', s);
    }
}

