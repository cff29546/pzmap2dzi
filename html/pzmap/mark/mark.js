import { g } from "../globals.js";
import * as util from "../util.js";
import { polylineLabelPos } from "../algorithm/geometry/geometry_utils.js";

class Mark {
    static DEFAULT = {
        // unique id of the mark
        id: '',

        // name of the mark
        name: '',

        // description text for the mark
        desc: '',

        // additional CSS classes for the mark
        class_list: undefined,

        // the minimal zoom level to show the mark
        // if not set, visible_zoom_level is set to 0 (visible at all zoom levels)
        visible_zoom_level: 0,

        // control if the mark is interactive
        // if true, the mark is not clickable and draggable
        // this is usually used for overlays such as 'rooms' and 'objects'
        passthrough: false,

        // CSS color value, used for the mark and text
        // if not set, the default CSS will take effect
        color: undefined,

        // CSS background value, used for the mark background
        // if not set, the default CSS will take effect
        background: undefined,

        // text font (optional):
        font: undefined,

        // position of the text:
        // 'none': the text is not displayed
        // 'abs(x,y)': the text is placed at the absolute position (x,y)
        //
        // (following is for area/polygon/polyline):
        // 'center' or undefined: the text is centered on the mark bbox
        // 'top': the text is placed at the top of rect with the smallest (x, y)
        //        (smallest x first, then smallest y if x's are equal)
        // 'centroid': the text is placed at the centroid of the mark
        text_position: 'center',

        text_color: undefined,
    };

    constructor(obj, keys) {
        this.keys = Object.keys(Mark.DEFAULT).concat(keys);
        for (const key of this.keys) {
            if (obj[key] === undefined) {
                if (Mark.DEFAULT[key] !== undefined) {
                    this[key] = Mark.DEFAULT[key];
                }
            } else {
                this[key] = obj[key];
            }
        }
        this.visible_zoom_level = Number(this.visible_zoom_level);
        if (!Number.isInteger(this.visible_zoom_level)) {
            this.visible_zoom_level = 0;
        }
        this.unselect();
    }

    cls() {
        const classList = [];
        if (this.selected) classList.push('selected');
        if (this.passthrough) {
            classList.push('passthrough');
        } else {
            classList.push('interactive');
        }
        if (this.class_list) {
            for (const cls of this.class_list) {
                classList.push(cls);
            }
        }
        return classList;
    }

    showOnUI() {
        const data = this.toObject();
        data.selected_index = this.selected_index;
        ui.setMarkerUIData(data);
    }

    select(idx=-1) {
        if (!this.selected || this.selected_index !== idx) {
            this.selected = true;
            this.selected_index = idx;
            this.resetHash();
        }
    }

    unselect() {
        if (this.selected !== false || this.selected_index !== -1) {
            this.selected = false;
            this.selected_index = -1;
            this.resetHash();
        }
    }

    toObject() {
        const o  = {type: this.constructor.name.toLowerCase()};
        for (const key of this.keys) {
            const value = structuredClone(this[key]);
            if (value !== Mark.DEFAULT[key]) {
                o[key] = value;
            }
        }
        return o;
    }

    copy() {
        return new this.constructor(this.toObject());
    }

    overwrite(obj) {
        const type = this.constructor.name.toLowerCase();
        if (types[type].validObject(obj)) {
            for (const key of this.keys) {
                if (key !== 'id' && obj[key] !== undefined && this[key] !== obj[key]) {
                    this[key] = obj[key];
                    this.resetHash();
                }
            }
            return true;
        }
        return false;
    }

    toRenderFormat(options = {}) {
        return {
            id: this.id, 
            type: this.constructor.name.toLowerCase(),
            color: this.color ? this.color : null,
            background: this.background ? this.background : null,
            name: this.name,
            layer: this.layer,
            hash: this.hash(options),
            interactive: !this.passthrough,
            isDiffSum: this.isDiffSum,
            cls: this.cls(),
            parts: this.parts(options)
        };
    }

    textPosition() {
        if (this.text_position === 'none') {
            return null;
        }
        if (this.centroid && this.text_position === 'centroid') {
            return this.centroid();
        }
        if (this.top && this.text_position === 'top') {
            return this.top();
        }
        if (this.dynamicLabelPos && this.text_position === 'dynamic') {
            return this.dynamicLabelPos();
        }
        if (typeof this.text_position === 'string') {
            const match = this.text_position.match(/^abs\((\d+),(\d+)\)$/);
            if (match) {
                return { x: Number(match[1]), y: Number(match[2]) };
            }
        }
        // default (center)
        const [x, y] = this.center(-1);
        return { x, y };
    }

    textPart(options = {}) {
        if (options.hide_text_level > g.zoomLevel || !this.name) {
            return null;
        }
        const pos = this.textPosition();
        if (!pos) {
            return null;
        }
        const text = { shape: 'text', text: this.name };
        Object.assign(text, pos);
        if (this.font) text.font = this.font;
        if (this.text_color) text.color = this.text_color;
        return text;
    }

    hash(options = {}) {
        if (!this._hash) {
            this._hash = util.uniqueId();
        }
        let text = options.hide_text_level > g.zoomLevel || !this.name ? '' : 't';
        if (text && this.dynamicLabelPos && this.text_position === 'dynamic') {
            const pos = this.dynamicLabelPos();
            if (pos) {
                text += Object.entries(pos).join(',');
            } else {
                text = '';
            }
        }
        return [this._hash, text, g.currentLayer].join(':');
    }

    resetHash() {
        this._hash = null;
    }
};

class Point extends Mark {
    static validObject(obj) {
        return (obj
            && (obj.name === undefined || typeof obj.name === 'string')
            && (obj.desc === undefined || typeof obj.desc === 'string')
            && (obj.visible_zoom_level === undefined || Number.isInteger(obj.visible_zoom_level))
            && Number.isInteger(obj.layer)
            && Number.isInteger(obj.x)
            && Number.isInteger(obj.y))
    }

    constructor(obj) { super(obj, ['x', 'y', 'layer']); }

    start_drag(x, y) {
        this.sx = this.x;
        this.sy = this.y;
    }

    drag(x, y) {
        this.x = this.sx + x;
        this.y = this.sy + y;
        this.resetHash();
    }

    update(obj) {
        this.overwrite(obj);
    }

    text() {
        return `(${this.x}, ${this.y} L ${this.layer})`;
    }

    center() {
        return [this.x, this.y];
    }

    bbox() {
        return { minX: this.x, minY: this.y, maxX: this.x + 1, maxY: this.y + 1 };
    }

    bboxDiffSum() {
        return {
            minDiff: this.x - this.y - 1,
            maxDiff: this.x - this.y + 1,
            minSum: this.x + this.y,
            maxSum: this.x + this.y + 2,
        };
    }

    parts(options = {}) {
        const allParts = [{ shape: 'point', x: this.x, y: this.y }];
        const text = this.textPart(options);
        if (text) {
            allParts.push(text);
        }
        return allParts;
    }
};

class Area extends Mark {
    static validRects(rects) {
        if (!Array.isArray(rects) || rects.length === 0) {
            return false;
        }
        for (const r of rects) {
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

    static validObject(obj) {
        return (obj
            && (obj.name === undefined || typeof obj.name === 'string')
            && (obj.desc === undefined || typeof obj.desc === 'string')
            && (obj.visible_zoom_level === undefined || Number.isInteger(obj.visible_zoom_level))
            && Number.isInteger(obj.layer)
            && Area.validRects(obj.rects));
    }

    constructor(obj) {
        super(obj, ['layer', 'rects']);
        if (this.class_list && this.class_list.includes('diff-sum')) {
            this.isDiffSum = true;
            // diff-sum mode
            // x = minDiff, y = minSum, width = maxDiff - minDiff, height = maxSum - minSum
        }
    }

    start_drag(x, y) {
        let idx = this.selected_index;
        if (idx < 0 || idx >= this.rects.length) {
            idx = 0;
        }
        if (this.isDiffSum) {
            const diff = x - y;
            const sum = x + y;
            x = diff;
            y = sum;
        }
        const r = this.rects[idx];
        this.sx = r.x;
        this.sy = r.y;
        this.sw = r.width;
        this.sh = r.height;
        // direction, true: right/bottom
        this.dx = x >= r.x + (r.width >> 1);
        this.dy = y >= r.y + (r.height >> 1);
    }

    drag(x, y) {
        let idx = this.selected_index;
        if (idx < 0 || idx >= this.rects.length) {
            idx = 0;
        }
        let finalX = this.sx + x;
        let finalY = this.sy + y;
        if (this.isDiffSum) {
            finalX = this.sx + x - y;
            finalY = this.sy + x + y;
        }
        const r = this.rects[idx];
        const dx = finalX - r.x;
        const dy = finalY - r.y;
        if (this.selected_index < 0) {
            for (const rect of this.rects) {
                rect.x += dx;
                rect.y += dy;
            }
        } else {
            r.x += dx;
            r.y += dy;
        }
        this.resetHash();
    }

    resize(x, y) {
        if (this.selected_index < 0 || this.selected_index >= this.rects.length) {
            return;
        }
        if (this.isDiffSum) {
            const diff = x - y;
            const sum = x + y;
            x = diff;
            y = sum;
        }
        const r = this.rects[this.selected_index];
        const fixX = this.sx + (this.dx ? 0 : this.sw);
        const moveX = this.sx + x + (this.dx ? this.sw : 0);
        r.x = fixX < moveX ? fixX : moveX;
        r.width = fixX < moveX ? moveX - fixX : fixX - moveX;
        r.width = r.width === 0 ? 1 : r.width;
        const fixY = this.sy + (this.dy ? 0 : this.sh);
        const moveY = this.sy + y + (this.dy ? this.sh : 0);
        r.y = fixY < moveY ? fixY : moveY;
        r.height = fixY < moveY ? moveY - fixY : fixY - moveY;
        r.height = r.height === 0 ? 1 : r.height;
        this.resetHash();
        return;
    }

    update(obj) {
        if (!Area.validObject(obj)) {
            if (Number.isInteger(obj.layer)) {
                this.layer = obj.layer;
            }
            if (Number.isInteger(obj.visible_zoom_level)) {
                this.visible_zoom_level = obj.visible_zoom_level;
            }
            this.name = obj.name;
            this.desc = obj.desc;
            this.resetHash();
            return;
        }
        if (this.selected_index < 0 || this.selected_index >= this.rects.length) {
            // no specific rect selected, overwrite the whole area
            this.overwrite(obj);
        } else {
            // replace the selected rect
            this.rects[this.selected_index] = obj.rects[0];
            obj.rects = this.rects;
            // overwrite other fields with obj
            this.overwrite(obj);
        }
    }

    append(x, y, width, height) {
        const r = { x, y, width, height };
        if (this.isDiffSum) {
            r.x = x - y; // diff
            r.y = x + y; // sum
        }
        this.rects.push(r);
        this.selected_index = this.rects.length - 1;
        this.resetHash();

    }

    removeSelectedRect() {
        if (this.selected_index < 0 || this.selected_index >= this.rects.length) {
            return 'nochange'; // no selected rect, keep the area
        }
        if (this.rects.length == 1) {
            return 'remove'; // remove the area
        }
        this.rects.splice(this.selected_index, 1);
        this.selected_index = -1; // unselect
        this.resetHash();
        return 'keep'; // keep rest of the area
    }

    text() {
        return `(${this.rects[0].x}, ${this.rects[0].y} L ${this.layer}, ${this.rects[0].width}x${this.rects[0].height})`;
    }

    center(idx = -1) {
        let x = 0, y = 0;
        if (idx < 0 || idx >= this.rects.length) {
            const { minX, minY, maxX, maxY } = this.bbox(); // already checked isDiffSum
            x = (minX + maxX) / 2;
            y = (minY + maxY) / 2;
            return [x, y];
        } else {
            const r = this.rects[idx];
            x = r.x + r.width / 2;
            y = r.y + r.height / 2;
            if (this.isDiffSum) {
                return [(x + y) / 2, (y - x) / 2];
            } else {
                return [x, y];
            }
        }
    }

    bbox() {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const r of this.rects) {
            const currentMinX = this.isDiffSum ? (r.x + r.y) / 2 : r.x;
            const currentMinY = this.isDiffSum ? (r.y - r.x - r.width) / 2 : r.y;
            const currentMaxX = this.isDiffSum ? (r.x + r.y + r.width + r.height) / 2 : r.x + r.width;
            const currentMaxY = this.isDiffSum ? (r.y + r.height - r.x) / 2 : r.y + r.height;
            if (currentMinX < minX) minX = currentMinX;
            if (currentMinY < minY) minY = currentMinY;
            if (currentMaxX > maxX) maxX = currentMaxX;
            if (currentMaxY > maxY) maxY = currentMaxY;
        }
        return { minX, minY, maxX, maxY };
    }

    bboxDiffSum() {
        let minDiff = Infinity, maxDiff = -Infinity, minSum = Infinity, maxSum = -Infinity;
        for (const r of this.rects) {
            const currentMinDiff = this.isDiffSum ? r.x : r.x - r.y - r.height;
            const currentMaxDiff = this.isDiffSum ? r.x + r.width : r.x + r.width - r.y;
            const currentMinSum = this.isDiffSum ? r.y : r.x + r.y;
            const currentMaxSum = this.isDiffSum ? r.y + r.height : r.x + r.width + r.y + r.height;
            if (currentMinDiff < minDiff) minDiff = currentMinDiff;
            if (currentMaxDiff > maxDiff) maxDiff = currentMaxDiff;
            if (currentMinSum < minSum) minSum = currentMinSum;
            if (currentMaxSum > maxSum) maxSum = currentMaxSum;
        }
        return { minDiff, maxDiff, minSum, maxSum };
    }

    centroid() {
        let weight = 0;
        let cx = 0, cy = 0;
        for (const r of this.rects) {
            const w = r.width * r.height;
            weight += w;
            cx += (r.x + r.width / 2) * w;
            cy += (r.y + r.height / 2) * w;
        }
        cx /= weight;
        cy /= weight;
        if (this.isDiffSum) {
            return { x: (cx + cy) / 2, y: (cx - cy) / 2 };
        } else {
            return { x: cx, y: cy };
        }
    }

    top() {
        let minX = Infinity, minY = Infinity;
        for (const r of this.rects) {
            if (r.x < minX || (r.x === minX && r.y < minY)) {
                minX = r.x;
                minY = r.y;
            }
        }
        return { x: minX, y: minY };
    }

    parts(options = {}) {
        const allParts = [];
        for (const r of this.rects) {
            const {x, y, width, height} = r;
            allParts.push({ shape: 'rect', x, y, width, height });
        }
        if (this.selected_index >= 0 && this.selected_index < this.rects.length) {
            allParts[this.selected_index].cls = ['selected-rect'];
        }
        const text = this.textPart(options);
        if (text) {
            allParts.push(text);
        }
        return allParts;
    }
};

class Polygon extends Mark {
    static validPoints(points) {
        if (!Array.isArray(points) || points.length < 2) {
            return false;
        }
        for (const p of points) {
            if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) {
                return false;
            }
        }
        return true;
    }

    static validObject(obj) {
        return (obj
            && (obj.name === undefined || typeof obj.name === 'string')
            && (obj.desc === undefined || typeof obj.desc === 'string')
            && (obj.visible_zoom_level === undefined || Number.isInteger(obj.visible_zoom_level))
            && Number.isInteger(obj.layer)
            && Polygon.validPoints(obj.points));
    }

    constructor(obj) {
        super(obj, ['layer', 'points', 'width', 'linecap', 'linejoin']);
    }

    text() {
        return this.points.map(p => `(${p.x}, ${p.y})`).join(' -> ');
    }

    bbox() {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const p of this.points) {
            if (p.x < minX) minX = p.x;
            if (p.y < minY) minY = p.y;
            if (p.x > maxX) maxX = p.x;
            if (p.y > maxY) maxY = p.y;
        }
        if (this.width) {
            minX -= this.width / 2;
            maxX += this.width / 2;
            minY -= this.width / 2;
            maxY += this.width / 2;
        }
        return { minX, minY, maxX, maxY };
    }

    bboxDiffSum() {
        let minDiff = Infinity, maxDiff = -Infinity, minSum = Infinity, maxSum = -Infinity;
        for (const p of this.points) {
            const currentDiff = p.x - p.y;
            const currentSum = p.x + p.y;
            if (currentDiff < minDiff) minDiff = currentDiff;
            if (currentDiff > maxDiff) maxDiff = currentDiff;
            if (currentSum < minSum) minSum = currentSum;
            if (currentSum > maxSum) maxSum = currentSum;
        }
        if (this.width) {
            minDiff -= this.width / 2;
            maxDiff += this.width / 2;
            minSum -= this.width;
            maxSum += this.width;
        }
        return { minDiff, maxDiff, minSum, maxSum };
    }

    center() {
        const { minX, minY, maxX, maxY } = this.bbox();
        return [(minX + maxX) / 2, (minY + maxY) / 2];
    }

    //centroid() {
    //    // TODO implement centroid for polygon
    //    // ref: https://en.wikipedia.org/wiki/Centroid#Of_a_polygon
    //}

    top() {
        let minX = Infinity, minY = Infinity;
        for (const p of this.points) {
            if (p.x < minX || (p.x === minX && p.y < minY)) {
                minX = p.x;
                minY = p.y;
            }
        }
        return { x: minX, y: minY };
    }

    parts(options = {}) {
        const allParts = [];
        const shape = this.constructor.name.toLowerCase();
        if (this.points.length) {
            allParts.push({
                shape,
                points: this.points,
                width: this.width || ((shape === 'polygon') ? 0 : 1),
                linecap: this.linecap,
                linejoin: this.linejoin,
        });
        }
        const text = this.textPart(options);
        if (text) {
            allParts.push(text);
        }
        return allParts;
    }
};

class Polyline extends Polygon {
    dynamicLabelPos() {
        const range = g.range;
        if (this.lastPos && this.zoomTimestamp === g.zoomInfo.timestamp) {
            const { x, y } = this.lastPos
            if (range.contains(x, y)) {
                return this.lastPos;
            }
        }
        this.lastPos = null;
        this.zoomTimestamp = g.zoomInfo.timestamp;
        const pos = polylineLabelPos(this.points, range);
        if (pos && range.contains(pos[0], pos[1])) {
            this.lastPos = { x: pos[0], y: pos[1], rotate: pos[2] };
        }
        return this.lastPos;
    }
}

export const types = {
    point: Point,
    area: Area,
    polygon: Polygon,
    polyline: Polyline,
};