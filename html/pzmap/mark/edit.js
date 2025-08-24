import * as ui from "../ui.js";
import * as util from "../util.js";
import * as i18n from "../i18n.js";
import * as c from "../coordinates.js";
import { g } from "../globals.js";
import { types } from "./mark.js";
import * as conf from "./conf.js";
import { MarkRender } from "./render.js";

export function create(obj) {
    if (!obj) return null;
    const type = types[obj.type];
    if (!type) {
        return null;
    }
    if (!obj.id) {
        obj.id = util.uniqueId();
    }
    return new type(obj);
}

export class MarkEditor {
    static MODE_NONE   = 0;
    static MODE_CREATE = 1;
    static MODE_MOVE   = 2;
    static MODE_RESIZE = 3;
    constructor(manager) {
        this.manager = manager;
        this.current = null;
        this.mode = MarkEditor.MODE_NONE;
        this.sx = 0;
        this.sy = 0;
        this.isDiffSum = false;
    }

    get() {
        return this.current;
    }

    select(id, idx) {
        if (this.current && this.current.id === id) {
            this.fromUI();
            if (this.current.selected_index === idx) return null;
        } else {
            this.unselect();
            const mark = this.manager.db.get(id);
            if (mark) {
                this.current = mark.copy();
                this.current.selected = true;
            }
        }
        if (this.current) {
            this.current.selected_index = idx;
            this.manager.render.upsert(this.current);
            this.updateStatus();
        }
        return true;
    }

    unselect() {
        if (this.current) {
            const id = this.current.id;
            this.current = null;
            this.manager.redraw(id);
            this.updateStatus();
        }
    }

    updateStatus() {
        if (this.current) {
            const state = this.manager.db.has(this.current.id) ? 'Select' : 'New';
            const cls = this.current.constructor.name;
            const text = this.current.text();
            const info = [i18n.T('Marker' + state)];
            if (this.current.isDiffSum) {
                info.push(i18n.T('MarkerDiffSum'));
            }
            info.push(i18n.T('Marker' + cls));
            info.push('[' + text + ']');
            this.current.showOnUI();
            util.setOutput('marker_output', 'Green', info.join(' '));
        } else {
            ui.setMarkerUIData({});
            util.setOutput('marker_output', 'Green', i18n.T('MarkerIdle'));
        }
    }

    fromUI(createNew = false) {
        const obj = ui.getMarkerUIData();
        if (this.current) {
            this.current.update(obj);
        } else if (createNew) {
            if (obj.missing.x || obj.missing.y) return;
            if (obj.width === 0 && obj.height === 0) {
                obj.type = 'point';
            } else {
                obj.type = 'area';
            }
            this.current = create(obj);
            if (this.current) {
                this.current.selected = true;
                this.current.selected_index = 0;
            }
        }
        if (this.current) {
            this.manager.render.upsert(this.current);
            this.updateStatus();
        }
    }

    fromData(obj) {
        if (!obj) return;
        this.unselect();
        this.current = create(obj);
        if (this.current) {
            this.current.selected = true;
            this.current.selected_index = 0;
        }
    }

    save() {
        if (!this.current) {
            this.fromUI(true); // create new mark from UI if not exists
        }
        if (this.current) {
            this.current.selected = false;
            this.current.selected_index = -1;
            this.manager.db.upsert(this.current);
            this.manager.redraw(this.current.id);
            this.current = null;
            this.updateStatus();
        }
    }

    focus() {
        if (!this.current) {
            this.fromUI(true); // create new mark from UI if not exists
        }
        if (this.current) {
            const [x, y] = this.current.center();
            const step = conf[g.map_type][this.current.visible_zoom_level].zoomToStep;
            c.zoomTo(x, y, this.current.layer, step);
            return true;
        }
        return false;
    }

    remove() {
        if (this.current) {
            const id = this.current.id;
            this.current = null;
            this.manager.remove(id);
            this.updateStatus();
        }
    }

    removeSingle() {
        if (!this.current) {
            return;
        }
        if (this.current.constructor.name === 'Area') {
            const result = this.current.removeSelectedRect();
            if (result === 'keep') {
                this.manager.render.upsert(this.current);
            }
            if (result === 'remove') {
                const id = this.current.id;
                this.current = null;
                this.manager.remove(id);
            } 
        } else {
            this.remove();
        }
        this.updateStatus();
    }

    click(event) {
        // return true to stop propagation
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
        // return true to stop propagation
        const e = event.originalEvent.target; // see OpenSeadragon press event
        if (event.originalEvent.shiftKey) {
            if (e && e.classList.contains('mark') && e.classList.contains('area')) {
                // resize existing
                const {id, index} = MarkRender.parseElementId(e.id);
                this.select(id, index);
                this._start_drag(event, MarkEditor.MODE_RESIZE);
                return true;
            } else {
                // create new
                this.isDiffSum = !!event.originalEvent.ctrlKey;
                this._start_drag(event, MarkEditor.MODE_CREATE);
                return true;
            }
        }
        if (e && e.classList.contains('mark')) {
            let {id, index} = MarkRender.parseElementId(e.id);
            if (!event.originalEvent.ctrlKey) index = -1; // select all mark
            this.select(id, index);
            this._start_drag(event, MarkEditor.MODE_MOVE);
            return true;
        }
        return false; // nothing hit, do not stop propagation
    }

    _start_drag(event, mode) {
        this.mode = mode;
        [this.sx, this.sy] = c.getSquare(event);
        if (this.mode === MarkEditor.MODE_NONE) return;
        if (this.current && this.mode !== MarkEditor.MODE_CREATE) {
            this.current.start_drag(this.sx, this.sy);
        }
    }

    drag(event) {
        if (this.mode === MarkEditor.MODE_NONE) return;
        const [x, y] = c.getSquare(event);
        const dx = x - this.sx;
        const dy = y - this.sy;
        if (this.mode === MarkEditor.MODE_MOVE) {
            if (this.current) {
                this.current.drag(dx, dy);
                this.manager.render.upsert(this.current);
                this.updateStatus();
            }
            return true;
        }
        if (this.mode === MarkEditor.MODE_CREATE) {
            if (!this.current || this.current.constructor.name !== 'Area') {
                this.fromData({
                    type: 'area', rects: [], layer: g.currentLayer,
                    visiable_zoom_level: ui.getMarkerUIData().visiable_zoom_level || 0,
                    class_list: this.isDiffSum ? ['diff-sum'] : undefined, 
                });
            }
            this.current.append(this.sx, this.sy, 1, 1);
            this.current.start_drag(this.sx, this.sy);
            this.mode = MarkEditor.MODE_RESIZE;
        }
        if (this.mode === MarkEditor.MODE_RESIZE) {
            if (this.current) {
                this.current.resize(dx, dy);
                this.manager.render.upsert(this.current);
            }
            this.updateStatus();
            return true;
        }
        return false;
    }

    release(event) {
        if (this.mode === MarkEditor.MODE_NONE) return;
        if (this.mode === MarkEditor.MODE_CREATE) {
            if (this.current) this.unselect();
            this.fromData({ type: 'point', x: this.sx, y: this.sy,
                visiable_zoom_level: ui.getMarkerUIData().visiable_zoom_level || 0,
                layer: g.currentLayer});
        }
        this.mode = MarkEditor.MODE_NONE;
        this.isDiffSum = false;
        if (this.current) {
            this.manager.render.upsert(this.current);
            this.updateStatus();
        }
        return true;
    }
}