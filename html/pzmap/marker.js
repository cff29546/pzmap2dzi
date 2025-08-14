import { g } from "./globals.js";
import * as i18n from "./i18n.js";
import * as c from "./coordinates.js";
import * as util from "./util.js";
import * as ui from "./ui.js";
import { types } from "./mark/mark.js";
import { MarkRender } from "./mark/render.js";
import { MarkDatabase } from "./mark/memdb.js";

var MARK_ZOOM_LEVEL_MIN_STEP = [
    0,     // level 0, always visible
    0.25,  // level 1, single square takes 0.25 pixels
    8      // level 2, single square takes 8 pixels
];
var ZOOM_TO_STEP = [
    0.2,   // level 0
    4,     // level 1
    16     // level 2
];
var POINT_SIZE = [
    10,    // level 0
    20,    // level 1
    30     // level 2
]
var POINT_BORDER_SIZE = [
    2,     // level 0
    2,     // level 1
    2      // level 2
]
var RECTANGLE_BORDER_SIZE = [
    8,      // level 0
    8,      // level 1
    8,      // level 2
    //16,     // level 1
    //24      // level 2
]

export function zoom() {
    // update zoom information to current viewer
    const zoom = c.getZoom(g.viewer, false);
    const step = zoom * g.base_map.sqr;
    let change = false;
    let zoomLevel = 1;
    while (step > MARK_ZOOM_LEVEL_MIN_STEP[zoomLevel]) {
        zoomLevel += 1;
    }
    zoomLevel -= 1; // zoom_level starts from 0
    if (g.zoomLevel != zoomLevel) {
        g.zoomLevel = zoomLevel;
        change = true;

        g.zoomInfo.rectBorder = RECTANGLE_BORDER_SIZE[zoomLevel];
        g.zoomInfo.pointBorder = POINT_BORDER_SIZE[zoomLevel];
        g.zoomInfo.pointSize = POINT_SIZE[zoomLevel];
        util.changeStyle('.point', 'width', g.zoomInfo.pointSize + 'px');
        util.changeStyle('.point', 'height', g.zoomInfo.pointSize + 'px');
        util.changeStyle('.point.text', 'padding-top', (g.zoomInfo.pointSize >> 1) + 'px');
        util.changeStyle('.area.rect.iso', 'border-width', g.zoomInfo.rectBorder + 'px');
        util.changeStyle('.area.rect.top', 'border-width', (g.zoomInfo.rectBorder >> 1) + 'px');
    }
    return change;
}


export class MarkManager {
    static originPoint = new types.point({
        id: 'origin', x: 0, y: 0, layer: 0, visiable_zoom_level: 0
    });

    constructor(options = {}) {
        const { onlyCurrentLayer = false, indexType = null, indexOptions = {} } = options;
        this.onlyCurrentLayer = onlyCurrentLayer;
        this.db = new MarkDatabase('top', onlyCurrentLayer, indexType, indexOptions);
        this.render = new MarkRender();
        this.editMark = null;
        this.hiddenType = {};
    }

    _new(obj = null) {
        if (obj === null) {
            return null;
        }
        const type = types[obj.type];
        if (!type) {
            return null;
        }
        if (!obj.id) {
            obj.id = util.uniqueId();
        }
        return new type(obj);
    }

    _range() {
        const layer = this.onlyCurrentLayer ? g.currentLayer : null;
        return c.getCanvasRange(g.viewer, g.base_map, layer);
    }

    _forceRefreshRender() {
        // inserting a dummy mark and removing it via fast timeout
        // force OpenSeadragon to refresh overlays
        this.render.upsert(MarkManager.originPoint);
        setTimeout(() => { this.render.remove(MarkManager.originPoint.id); }, 1);
    }

    setVisiableType(type, value) {
        if (!!this.hiddenType[type] !== !value) {
            this.hiddenType[type] = !value;
            this.redrawAll();
            this._forceRefreshRender();
        }
    }

    setTextVisibility(visible) {
        this.render.setRenderOptions('hide_text', !visible);
        this.redrawAll();
        this._forceRefreshRender();
    }

    remove(id) {
        this.db.remove(id);
        this.render.remove(id);
    }

    update() {
        if (this.editMark) {
            const state = this.db.has(this.editMark.id) ? 'Select' : 'New';
            const cls = this.editMark.constructor.name;
            const text = this.editMark.text();
            const info = i18n.T('Marker' + state) + ' ' + i18n.T('Marker' + cls) + ' [' + text + ']';
            this.editMark.showOnUI();
            util.setOutput('marker_output', 'Green', info);
        } else {
            ui.setMarkerUIData({});
            util.setOutput('marker_output', 'Green', i18n.T('MarkerIdle'));
        }
    }

    updateByInput(obj) {
        if (this.editMark) {
            this.editMark.update(obj);
            this.render.upsert(this.editMark);
            this.update();
        }
    }

    unSelect() {
        if (this.editMark) {
            const id = this.editMark.id;
            if (this.db.has(id)) {
                const mark = this.db.get(id, this._range());
                if (mark) {
                    this.render.upsert(mark);
                }
            } else {
                this.remove(id);
            }
            this.editMark = null;
        }
        this.update();
    }

    select(id, idx) {
        if (this.editMark) {
            if (this.editMark.id === id) {
                this.Input();
                if (this.editMark.selected_index === idx) return;
                this.editMark.selected_index = idx;
                this.render.upsert(this.editMark);
                return true;
            } else {
                this.unSelect();
            }
        }
        const mark = this.db.get(id);
        if (!mark) {
            return false;
        }
        this.editMark = this._new(mark.toObject());
        this.editMark.selected = true;
        this.editMark.selected_index = idx;
        this.render.upsert(this.editMark);
    }

    changeMode(mode = null) {
        if (!mode) {
            mode = g.map_type || 'top';
        }
        this.db.changeMode(mode);
        this.clearRenderCache();
    }

    clearRenderCache() {
        this.render.sync([]);
    }

    redrawAll() {
        let marks = this.db.query(this._range(), g.currentLayer, g.zoomLevel);
        for (const type in this.hiddenType) {
            if (this.hiddenType[type]) {
                marks = marks.filter(m => m.constructor.name !== type);
            }
        }
        if (this.editMark) {
            const editId = this.editMark.id;
            marks = marks.filter(m => m.id !== editId);
            marks.push(this.editMark);
        }
        this.render.sync(marks);
    }

    createNew(obj=null) {
        if (obj === null) {
            obj = ui.getMarkerUIData();
        }
        if (obj.invalid) {
            return false;
        }
        if (types.point.validObject(obj)) {
            obj.type = 'point';
        }
        if (types.area.validObject(obj)) {
            obj.type = 'area';
        }
        if (!obj.type) {
            return false;
        }
        this.unSelect();
        this.editMark = this._new(obj);
        this.editMark.selected = true;
        this.editMark.selected_index = 0;
        this.render.upsert(this.editMark);
        this.update();
        return true;
    }

    click(event) {
        if (event.originalEvent.shiftKey) {
            // create new marker
            return true;
        }
        const element = event.originalTarget; // see OpenSeadragon click event
        if (element && element.classList.contains('mark')) {
            // select existing marker
            return true;
        }
        // click on empty area
        return false;
    }

    press(event) {
        const e = event.originalEvent.target; // see OpenSeadragon press event
        const [x, y] = c.getSquare(event);
        const s = {x, y};
        const shift = event.originalEvent.shiftKey;
        const ctrl = event.originalEvent.ctrlKey;
        if (shift) {
            this.dragging = 'press';
            this.start = s;
            return true;
        } else {
            if (e && e.classList.contains('mark')) {
                this.selectElement(e, ctrl);
                if (this.editMark) {
                    this.editMark.start_drag();
                    this.dragging = 'move';
                    this.start = s;
                    return true;
                }
            }
        }
        return false;
    }

    selectElement(e, ctrl) {
        const {name, type, index, id} = MarkRender.parseElementId(e.id);
        if (!ctrl) {
             this.select(id, -1);
        } else {
            this.select(id, index);
        }
        this.update();
    }

    drag(event) {
        if (!this.dragging) {
            return false;
        }
        const [x, y] = c.getSquare(event);
        if (this.dragging == 'move') {
            if (this.editMark) {
                this.editMark.drag(x - this.start.x, y - this.start.y);
                this.render.upsert(this.editMark);
            }
            this.update();
            return true;
        }
        if (this.dragging == 'press') { // create new area
            this.dragging = 0;
            const obj = {
                rects: [{ x: this.start.x, y: this.start.y, width: 1, height: 1 }],
                layer: g.currentLayer
            };
            if (this.editMark && this.editMark.constructor.name === 'Area') {
                this.editMark.append(obj);
            } else {
                const uiData = ui.getMarkerUIData();
                obj.visiable_zoom_level = uiData.visiable_zoom_level || 0;
                this.createNew(obj);
            }
            if (this.editMark) {
                this.editMark.start_drag();
                this.dragging = 'resize';
            }
        }
        if (this.dragging == 'resize') {
            if (this.editMark) {
                this.editMark.resize(x - this.start.x, y - this.start.y);
                this.render.upsert(this.editMark);
            }
            this.update();
            return true;
        }
        return false;
    }

    release(event) {
        if (this.dragging) {
            if (this.dragging == 'resize') {
                this.editMark.showOnUI();
            }
            if (this.dragging == 'press') { // create new point
                const uiData = ui.getMarkerUIData();
                const obj = {
                    x: this.start.x, y: this.start.y,
                    layer: g.currentLayer,
                    visiable_zoom_level: uiData.visiable_zoom_level || 0
                };
                this.createNew(obj);
            }
            if (this.dragging == 'move') {
                // nothing to do, just stop dragging
            }
            this.dragging = 0;
            return true;
        }
        return false;
    }

    focusSelected() {
        if (!this.editMark) {
            this.createNew();
        }
        if (this.editMark) {
            const [x, y] = this.editMark.center();
            const step = ZOOM_TO_STEP[this.editMark.visiable_zoom_level];
            c.zoomTo(x, y, this.editMark.layer, step);
            return true;
        }
        return false;
    }

    save() {
        if (!this.editMark) {
            this.createNew(); // create new mark from UI if not exists
        }
        if (this.editMark) { // selecting & new
            this.editMark.selected = false;
            this.editMark.selected_index = -1;
            if (this.db.upsert(this.editMark, this._range())) {
                this.render.upsert(this.editMark);
            } else {
                this.render.remove(this.editMark.id);
            }
            this.editMark = null;
            this.update();
        }
    }

    removeSelected() {
        if (!this.editMark) {
            return;
        }
        const id = this.editMark.id;
        this.editMark = null;
        this.remove(id);
        this.update();
    }

    removeSelectedSingle() {
        if (!this.editMark) {
            return;
        }
        if (this.editMark.constructor.name === 'Area') {
            const result = this.editMark.removeSelectedRect();
            if (result === 'keep') {
                this.render.upsert(this.editMark);
                this.update();
            }
            if (result === 'remove') {
                const id = this.editMark.id;
                this.editMark = null;
                this.remove(id);
                this.update();
            } 
        } else {
            this.removeSelected();
        }
    }

    removeAll() {
        this.clearRenderCache();
        this.db.clear();
        this.editMark = null;
        this.update();
    }

    Input(event = null) {
        const obj = ui.getMarkerUIData();
        this.updateByInput(obj);
    }

    load(objects, refresh = true) {
        if (!Array.isArray(objects)) {
            return;
        }
        const marks = [];
        for (const obj of objects) {
            if (!util.isObject(obj) || typeof obj.id !== 'string') {
                continue;
            }

            if ((obj.type === 'point' && types.point.validObject(obj))
                || (obj.type === 'area' && types.area.validObject(obj))) {
                marks.push(this._new(obj));
            }
        }
        this.db.batchInsert(marks);
        this.redrawAll();
        if (refresh) {
            this._forceRefreshRender();
        }
    }

    loadDefault(lang = null, failed = '') {
        if (!lang) lang = i18n.getLang();
        const path = './pzmap/i18n/marks_' + lang +'.json';
        failed = failed ? failed + ',' + lang : lang;
        return window.fetch(path)
            .then((r)=>r.json())
            .then((obj) => {this.load(obj); return Promise.resolve(obj);})
            .catch((e)=> {
                util.setOutput('marker_output', 'Red', i18n.T('MarkerLoadDefaultFail', { lang: failed }));
                if (lang !== 'en') return this.loadDefault('en', failed);
                return Promise.resolve([]);
        });
    }

    Import() {
        util.upload().then((data) => {
            if (data) {
                const json = util.parseJson(data);
                if (json) {
                    this.load(json);
                }
            }
        });
    };

    Export() {
        this.unSelect();
        const data = [];
        for (const mark of this.db.all()) {
            data.push(mark.toObject());
        }
        const s = JSON.stringify(data, null, '  ');
        util.download('marks.json', s);
    }
}

