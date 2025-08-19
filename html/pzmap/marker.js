import { g } from "./globals.js";
import * as i18n from "./i18n.js";
import * as c from "./coordinates.js";
import * as util from "./util.js";
import * as ui from "./ui.js";
import { types } from "./mark/mark.js";
import { MarkRender } from "./mark/render.js";
import { MarkDatabase } from "./mark/memdb.js";
import { MarkEditor, create } from "./mark/edit.js";
import {
    MARK_ZOOM_LEVEL_MIN_STEP,
    POINT_SIZE,
    POINT_BORDER_SIZE,
    RECTANGLE_BORDER_SIZE,
    ZOOM_TO_STEP,
} from "./mark/conf.js";

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
        util.changeStyle('.area.rect.diff-sum.iso', 'border-width', (g.zoomInfo.rectBorder >> 1) + 'px');
    }
    return change;
}

export class MarkManager {
    static originPoint = new types.point({
        id: 'origin', x: 0, y: 0, layer: 0, visiable_zoom_level: 0
    });

    constructor(options = {}) {
        const {
            onlyCurrentLayer = false,
            enableEdit = false,
            indexType = null,
            indexOptions = {},
        } = options;
        this.enabled = true;
        this.onlyCurrentLayer = onlyCurrentLayer;
        this.db = new MarkDatabase('top', onlyCurrentLayer, indexType, indexOptions);
        this.render = new MarkRender();
        this.hiddenType = {};
        this.edit = enableEdit ? new MarkEditor(this) : null;
    }

    enable() {
        this.enabled = true;
        this.clearRenderCache();
        this.redrawAll();
    }

    disable() {
        this.enabled = false;
        this.clearRenderCache();
    }

    _range() {
        const layer = this.onlyCurrentLayer ? g.currentLayer : null;
        return c.getCanvasRange(g.viewer, g.base_map, layer);
    }

    setVisiableType(type, value) {
        if (!!this.hiddenType[type] !== !value) {
            this.hiddenType[type] = !value;
            this.redrawAll();
        }
    }

    setTextVisibility(visible) {
        this.render.setRenderOptions('hide_text', !visible);
        this.redrawAll();
    }

    clearRenderCache() {
        this.render.sync([]);
    }

    remove(id) {
        this.db.remove(id);
        this.render.remove(id);
    }

    removeAll() {
        this.db.clear();
        this.clearRenderCache();
        if (this.edit) this.edit.remove();
    }

    redraw(id) {
        if (!this.enabled) return;
        if (this.db.has(id)) {
            const mark = this.db.get(id, this._range());
            if (mark) {
                this.render.upsert(mark);
            }
        } else {
            this.remove(id);
        }
    }

    redrawAll() {
        if (!this.enabled) return;
        const result = this.db.query(this._range(), g.currentLayer, g.zoomLevel);
        const marks = [];
        if (this.edit) {
            const current = this.edit.get();
            if (current) marks.push(current);
        }
        for (const mark of result) {
            if (!this.hiddenType[mark.constructor.name]) {
                marks.push(mark);
            }
        }
        this.render.sync(marks);
    }

    changeMode(mode = null) {
        if (!mode) {
            mode = g.map_type || 'top';
        }
        this.db.changeMode(mode);
        this.clearRenderCache();
    }

    load(objects) {
        if (!Array.isArray(objects)) {
            return;
        }
        const marks = [];
        for (const obj of objects) {
            if (!util.isObject(obj) || typeof obj.id !== 'string') {
                continue;
            }

            if (types[obj.type] && types[obj.type].validObject(obj)) {
                marks.push(create(obj));
            }
        }
        this.db.batchInsert(marks);
        this.redrawAll();
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
        const data = [];
        for (const mark of this.db.all()) {
            data.push(mark.toObject());
        }
        const s = JSON.stringify(data, null, '  ');
        util.download('marks.json', s);
    }
}

