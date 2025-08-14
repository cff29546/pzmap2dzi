import { g } from "../globals.js";
import * as util from "../util.js";
import * as c from "../coordinates.js";
import * as draw from "./draw.js";

var _RENDER_MAP = {};
export function reset() {
    for (const key in _RENDER_MAP) {
        const render = _RENDER_MAP[key];
        render.sync([]); // clear all marks
    }
    _RENDER_MAP = {};
}

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
// text: { x: <x>, y: <y>, text: 'text content', font: '12px Arial' }

export class MarkRender {
    static parseElementId(elementId) {
        const [name, type, idx, ...rest] = elementId.split('-');
        const id = rest.join('-');
        return { name, type, index: parseInt(idx), id };
    }

    constructor(options = {}) {
        const { name = null, renderOptions = {} } = options;
        if (name !== null && _RENDER_MAP[name] === undefined) {
            this.name = name.replace(/-/g, '_');
        } else {
            this.name = util.uniqueId();
        }
        _RENDER_MAP[this.name] = this;
        this.marks = {};
        this.renderOptions = renderOptions;
    }

    _remove(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            g.viewer.removeOverlay(element);
        }
    }

    _render(id) {
        const mark = this.marks[id];
        if (!mark) return;

        //marker level preparation, modify parts if needed
        draw.processMark(mark);

        for (let i = 0; i < mark.parts.length; i++) {
            const part = mark.parts[i];
            const eid = this._eid(id, mark.type, i);
            draw.drawPart(eid, mark, part);
        }
    }

    _eid(id, type, i) {
        return [this.name, type, i, id].join('-');
    }

    setRenderOptions(key, value) {
        this.renderOptions[key] = value;
    }

    remove(id) {
        const mark = this.marks[id];
        if (mark) {
            for (let i = 0; i < mark.parts.length; i++) { // need length check
                this._remove(this._eid(id, mark.type, i));
            }
            delete this.marks[id];
        }
    }

    upsert(mark) {
        // add or update a mark
        // returns the id of the mark if it was added or updated
        const newMark = mark.toRenderFormat(this.renderOptions);
        if (!newMark || !newMark.id) return null;
        if (!newMark.hash) newMark.hash = util.uniqueId();
        const id = newMark.id;
        const oldMark = this.marks[id];
        if (oldMark) {
            if (oldMark.id === id && oldMark.hash === newMark.hash) {
                // no changes, nothing to do
                return id;
            }
            this.remove(id);
        }
        this.marks[id] = newMark;
        this._render(id);
        return id;
    }

    sync(marks) {
        const ids = Object.keys(this.marks);
        const newIds = new Set();
        for (const mark of marks) {
            const id = this.upsert(mark);
            if (id) newIds.add(id);
        }
        for (const id of ids) {
            if (!newIds.has(id)) {
                this.remove(id);
            }
        }
    }
}