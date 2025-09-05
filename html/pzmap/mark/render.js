import { g } from "../globals.js";
import * as util from "../util.js";
import * as OSDOverlayDraw from "./osd_draw.js";
import * as SVGOverlayDraw from "./svg_draw.js";

// render format:
// {
//   id: 'mark-id',
//   name: 'mark-name',
//   type: 'point' | 'area' | ...,
//   layer: <layer number>, // layer number for the mark
//   cls: ['cls1', 'cls2', ...], // CSS classes for the mark (applied to all parts)
//   color: <CSS color value> (optional), // color for the mark
//   background: <CSS background value> (optional), // background for the mark
//   font: <CSS font value> (optional), // font for the text
//
//   // unique hash for the mark
//   // based on its renderable content
//   // used to detect changes
//   hash: '',
//
//   // renderable parts of the mark
//   parts: [
//     {
//       shape: 'point' | 'rect' | 'text' | 'polyline' | 'polygon' | ...,
//       cls: 'cls1 cls2 ...', // CSS classes
//
//       // shape specific properties
//       x: <x>, // for point and rect
//       y: <y>, // for point and rect
//       text: 'text content',
//       ...
//     }
//   ]
// }
//
// parts specification:
// point: { x: <x>, y: <y> }
// rect: { x: <xmin>, y: <ymin>, width: <width>, height: <height> }
// text: { x: <x>, y: <y>, text: <text>, font: <font> }
// polyline: { points: [{ x: <x1>, y: <y1> }, { x: <x2>, y: <y2> }, ...] }
// polygon: { points: [{ x: <x1>, y: <y1> }, { x: <x2>, y: <y2> }, ...] }

export class MarkRender {
    static parseElementId(elementId) {
        const parts = elementId.split('-');
        const name = parts[0];
        const type = parts[1];
        const id = parts[2];
        const idx = parts[3];
        const index = Number.parseInt(idx);
        return { name, type, index: Number.isInteger(index) ? index : idx, id };
    }
    static RENDER_METHODS = {
        osd: OSDOverlayDraw,
        svg: SVGOverlayDraw,
    };

    constructor(options = {}) {
        const {
            name = null,
            formatterOptions = {},
            renderMethod = 'osd',
        } = options;
        if (name) {
            this.name = name.replace(/-/g, '_');
        } else {
            this.name = util.uniqueId();
        }
        this.marks = {};
        this.formatterOptions = formatterOptions;
        this.renderMethod = renderMethod;
        this.draw = MarkRender.RENDER_METHODS[renderMethod] || MarkRender.RENDER_METHODS.OSD;
    }

    _eid(id, type, i) {
        return [this.name, type, id, i].join('-');
    }

    setFormatterOptions(key, value) {
        this.formatterOptions[key] = value;
    }

    remove(id) {
        const mark = this.marks[id];
        if (mark) {
            const markId = this._eid(id, mark.type, 'x');
            if (this.draw.removeMark(markId)) {
                for (let i = 0; i < mark.parts.length; i++) { // need length check
                    this._remove(this._eid(id, mark.type, i));
                }
            }
            delete this.marks[id];
        }
    }

    _remove(elementId) {
        this.draw.removePart(elementId);
    }

    _render(id) {
        const mark = this.marks[id];
        if (!mark) return;

        const markId = this._eid(id, mark.type, 'x');
        if (this.draw.addMark(markId, mark)) {
            for (let i = 0; i < mark.parts.length; i++) {
                const part = mark.parts[i];
                const partId = this._eid(id, mark.type, i);
                this.draw.addPart(partId, mark, part);
            }
        }
    }

    upsert(mark) {
        const newMark = mark.toRenderFormat(this.formatterOptions);
        this._upsert(newMark);
    }

    sync(marks) {
        const oldIds = Object.keys(this.marks);
        const newIds = new Set();
        for (const mark of marks) {
            const newMark = mark.toRenderFormat(this.formatterOptions);
            if (newIds.has(newMark.id)) continue; // only first mark
            this._upsert(newMark);
            newIds.add(newMark.id);
        }
        for (const id of oldIds) {
            if (!newIds.has(id)) {
                this.remove(id);
            }
        }
        if (this.draw.refresh && newIds.size > 0) {
            this.draw.refresh();
        }
    }

    _upsert(newMark) {
        if (!newMark || !newMark.id) return false;
        if (!newMark.hash) newMark.hash = util.uniqueId();
        const id = newMark.id;
        const oldMark = this.marks[id];
        if (oldMark) {
            if (oldMark.id === id && oldMark.hash === newMark.hash) {
                // no changes, nothing to do
                return false;
            }
            this.remove(id);
        }
        this.marks[id] = newMark;
        this._render(id);
        return true;
    }
}