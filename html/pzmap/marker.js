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
var POINT_SIZE = [
    10,    // level 0
    20,    // level 1
    30     // level 2
]
var BORDER_SIZE = [
    8,      // level 0
    16,     // level 1
    24      // level 2
]

var CURRENT = {
    zoom_level: null,
}

export function zoom() {
    // canvas event
    let change = false;
    let zoom = c.getZoom(g.viewer, false);
    let step = zoom * g.base_map.sqr;
    let zoom_level = 1;
    while (step > ZOOM_LEVEL_STEP_SIZE[zoom_level]) {
        zoom_level += 1;
    }
    zoom_level -= 1; // zoom_level starts from 0
    if (CURRENT.zoom_level != zoom_level) {
        CURRENT.zoom_level = zoom_level;
        util.changeStyle('.point', 'width', POINT_SIZE[zoom_level] + 'px');
        util.changeStyle('.point', 'height', POINT_SIZE[zoom_level] + 'px');
        util.changeStyle('.area-iso', 'border-width', BORDER_SIZE[zoom_level] + 'px');
        util.changeStyle('.area-top', 'border-width', (BORDER_SIZE[zoom_level]>>1) + 'px');

        // update visibility when zoom level changed
        for (let level in ZOOM_LEVEL_STEP_SIZE) {
            util.changeStyle('.zoom' + level, 'visibility', level <= zoom_level ? 'visible' : 'hidden');
            util.changeStyle('.zoom' + level, 'pointer-events', level <= zoom_level ? 'auto' : 'none');
            util.changeStyle('.passthrough-zoom' + level, 'visibility', level <= zoom_level ? 'visible' : 'hidden');
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
        if (g.map_type != 'top') {
            element.style.transform = 'matrix(0.5, 0.25, -0.5, 0.25, 0, 0)';
        }
        element.style.width = size.x + 'px';
        element.style.height = size.y + 'px';
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

function getIdx(e) {
    let idx = parseInt(e.id.split('-')[1]);
    return idx;
}

class Mark {
    constructor(obj, keys) {
        this.selected = false;
        this.removed = false;
        this.backup = {};
        this.keys = Object.keys(DEFAULT_MARKER_OPTIONS).concat(keys);
        this.mkeys = [];
        this.non_restoreable = [];
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

    setSelect(flag, update=null) {
        if (update || this.selected !== flag) {
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
        ui.setMarkerUIData(this.toObject(true));
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
            if (!this.non_restoreable.includes(key)) {
                this[key] = value;
            }
        }
        this.updateOverlay();
    }

    toObject(mutable=false) {
        let o  = {type: this.constructor.name.toLowerCase()};
        for (let key of this.keys) {
            o[key] = structuredClone(this[key]);
        }
        if (mutable) {
            for (let key of this.mkeys) {
                o[key] = structuredClone(this[key]);
            }
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

    setSelect(flag, idx) {
        super.setSelect(flag, false);
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

    update(obj) {
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
    constructor(obj) {
        super(obj, ['layer', 'rects']);
        this.selected_rect = -1;
        this.rect_rendered = 0;
        this.mkeys = ['selected_rect'];
        this.non_restoreable = ['rect_rendered'];
    }

    updateOverlay() {
        let i = 0;
        let rendered = 0;
        for (i = 0; i < this.rects.length; i++) {
            let aid = 'ma-' + i + '-' + this.id;
            if (this.removed) {
                removeOverlay(aid);
            } else {
                let r = this.rects[i];
                let c = this.cls();
                let idx = this.selected_rect;
                if (i == idx && this.selected) {
                    c.push('selected-rect');
                }
                let e = overlayRect(aid, c, this.name, r.x, r.y, this.layer, r.width, r.height);
                rendered = Math.max(i, rendered);
            }
        }
        while (i <= this.rect_rendered) {
            let aid = 'ma-' + i + '-' + this.id;
            removeOverlay(aid);
            i += 1;
        }
        this.rect_rendered = rendered;
    }

    setSelect(flag, idx=null) {
        let update = false;
        if (idx !== null && this.selected_rect !== idx) {
            update = true;
            this.selected_rect = idx;
        }
        super.setSelect(flag, update);
    }

    removeSelectedRect() {
        if (this.rects.length == 1) {
            return false; // remove the area
        }
        if (this.selected_rect < 0 || this.selected_rect >= this.rects.length) {
            return true; // no selected rect, keep the area
        }
        this.getBackup();
        this.rects.splice(this.selected_rect, 1);
        this.updateOverlay();
        return true; // keep rest of the area
    }

    start_drag() {
        let idx = this.selected_rect;
        if (idx < 0 || idx >= this.rects.length) {
            idx = 0;
        }
        this.sx = this.rects[idx].x;
        this.sy = this.rects[idx].y;
        this.sw = this.rects[idx].width;
        this.sh = this.rects[idx].height;
    }

    drag(x, y) {
        let obj = this.toObject();
        let idx = this.selected_rect;
        if (idx < 0 || idx >= this.rects.length) {
            idx = 0;
        }
        let r = this.rects[idx];
        let dx = this.sx + x - r.x;
        let dy = this.sy + y - r.y;
        if (this.selected_rect < 0) {
            for (let i in obj.rects) {
                obj.rects[i].x += dx;
                obj.rects[i].y += dy;
            }
        } else {
            obj.rects[idx].x += dx;
            obj.rects[idx].y += dy;
        }
        this.move(obj);
    }

    resize(x, y) {
        let idx = this.selected_rect;
        if (idx < 0 || idx >= this.rects.length) {
            return;
        }
        let obj = this.toObject();
        if (x < 0) {
            obj.rects[idx].x = this.sx + x;
            obj.rects[idx].width = this.sw - x;
        } else {
            obj.rects[idx].x = this.sx;
            obj.rects[idx].width = this.sw + x;
        }
        if (y < 0) {
            obj.rects[idx].y = this.sy + y;
            obj.rects[idx].height = this.sh - y;
        } else {
            obj.rects[idx].y = this.sy;
            obj.rects[idx].height = this.sh + y;
        }
        this.move(obj);
    }

    update(obj) {
        if (obj.selected_rect !== undefined) {
            this.move(obj);
        } else {
            if (is_legal.area(obj)) {
                let r = obj.rects[0];
                obj.rects = this.rects.slice(0); // copy existing rects
                let idx = this.selected_rect;
                if (idx < 0 || idx >= this.rects.length) {
                    idx = 0;
                }
                obj.rects[idx] = r; // replace the selected rect
                this.move(obj);
            }
        }
    }

    append(obj) {
        if (is_legal.area(obj)) {
            let r = obj.rects[0];
            obj.rects = this.rects.slice(0); // copy existing rects
            obj.rects.push(r); // add new rect
            this.selected_rect = obj.rects.length - 1;
            this.move(obj);
        }
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
            m.update(obj);
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

    select(id, idx) {
        if (id !== this.sid) {
            this.unSelect();
        }
        let m = this.markers[id];
        if (m) {
            m.setSelect(true, idx);
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
            if(this.select(uid, -1)) {
                this.new_id = uid;
            }
        }
        this.update();
        return true;
    }

    click(event) {
        let shift = event.originalEvent.shiftKey;
        if (shift) {
            // create new marker
            return true;
        }
        let e = event.originalTarget; // see OpenSeadragon click event
        if (e && e.classList.contains('mark')) {
            // select existing marker
            return true;
        }
        // click on empty area
        return false;
    }

    press(event) {
        let e = event.originalEvent.target; // see OpenSeadragon press event
        let [x, y] = c.getSquare(event);
        let s = {x:x, y:y};
        let shift = event.originalEvent.shiftKey;
        let ctrl = event.originalEvent.ctrlKey;
        if (shift) {
            this.dragging = 'press';
            this.start = s;
            return true;
        } else {
            if (e && e.classList.contains('mark')) {
                this.selectElement(e, ctrl);
                let m = this.markers[this.sid];
                if (m) {
                    m.start_drag();
                    this.dragging = 'move';
                    this.start = s;
                    return true;
                }
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
        if (this.dragging == 'press') { // create new area
            this.dragging = 0;
            let m = this.markers[this.sid];
            let obj = {
                rects: [{x: this.start.x, y: this.start.y, width: 1, height: 1}],
                layer: g.currentLayer
            }; // new area
            obj = Object.assign(obj, DEFAULT_MARKER_OPTIONS);
            if (m && m.constructor.name === 'Area') {
                m.append(obj);
            } else {
                this.createNew(obj);
                m = this.markers[this.sid];
                m.setSelect(true, 0);
            }
            if (m) {
                m.start_drag();
                this.dragging = 'resize';
            }
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
                m.showOnUI();
            }
            if (this.dragging == 'press') {
                let obj = {x: this.start.x, y: this.start.y, layer: g.currentLayer}; // new point
                this.createNew(Object.assign(obj, DEFAULT_MARKER_OPTIONS));
            }
            this.dragging = 0;
            return true;
        }
        return false;
    }

    // ui event
    selectElement(e, ctrl) {
        let id = getId(e);
        let idx = -1;
        if (ctrl) {
            idx = getIdx(e);
        }
        this.select(id, idx);
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

    removeSelectedSingle() {
        let m = this.markers[this.sid];
        if (m && m.constructor.name === 'Area' && m.removeSelectedRect()) {
            this.update();
        } else {
            this.removeSelected();
        }
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

