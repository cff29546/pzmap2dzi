import { g } from "../globals.js";

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
        // if not set, visiable_zoom_level is set to 0 (visible at all zoom levels)
        visiable_zoom_level: 0,

        // control if the mark is interactive
        // if true, the mark is not clickable and draggable
        // this is usually used for overlays such as 'room' and 'objects'
        passthrough: undefined,

        // CSS color value, used for the mark and text
        // if not set, the default CSS will take effect
        color: undefined,

        // CSS background value, used for the mark background
        // if not set, the default CSS will take effect
        background: undefined,

        // text font (optional):
        font: undefined,

        // position of the text (only for area marks):
        // 'center' or undefined: the text is centered on the mark bbox
        // 'top': the text is placed at the top of rect with the smallest (x, y)
        //        (smallest x first, then smallest y if x's are equal)
        // 'centroid': the text is placed at the centroid of the mark
        // 'abs(x,y)': the text is placed at the absolute position (x,y)
        text_position: undefined,
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
        this.visiable_zoom_level = Number(this.visiable_zoom_level);
        if (!Number.isInteger(this.visiable_zoom_level)) {
            this.visiable_zoom_level = 0;
        }
        this.selected = false;
        this.selected_index = -1; // selected part index
    }

    cls() {
        const classList = [];
        if (this.selected) classList.push('selected');
        if (this.passthrough) {
            classList.push('passthrough');
        } else {
            classList.push('interactive');
        }
        if (this.class_list) classList.push(...this.class_list);
        return classList;
    }

    showOnUI() {
        const data = this.toObject();
        data.selected_index = this.selected_index;
        ui.setMarkerUIData(data);
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

    overwrite(obj) {
        const type = this.constructor.name.toLowerCase();
        if (types[type].validObject(obj)) {
            for (const key of this.keys) {
                if (key !== 'id') {
                    this[key] = obj[key];
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
            cls: this.cls(),
            parts: this.parts(options)
        };
    }

    textPosition() {
        if (this.centroid && this.text_position === 'centroid') {
            return this.centroid();
        }
        if (this.top && this.text_position === 'top') {
            return this.top();
        }
        if (typeof this.text_position === 'string') {
            const match = this.text_position.match(/^abs\((\d+),(\d+)\)$/);
            if (match) {
                return [Number(match[1]), Number(match[2])];
            }
        }
        // default (center)
        return this.center(-1);
    }

    textPart(options = {}) {
        if (options.hide_text || !this.name) {
            return null;
        }
        const [cx, cy] = this.textPosition();
        const text = { shape: 'text', x: cx, y: cy, text: this.name };
        if (this.font) {
            text.font = this.font;
        }
        return text;
    }

    commonHash(keys = null, options = {}) {
        if (!keys) keys = [];
        keys.push(this.selected ? this.selected_index : 'x');
        keys.push(this.passthrough ? '1' : '0');
        keys.push(options.hide_text ? '' : this.name);
        keys.push(this.layer);
        keys.push(g.currentLayer);
        return keys;
    }
};

class Point extends Mark {
    static validObject(obj) {
        return (obj
            && (obj.name === undefined || typeof obj.name === 'string')
            && (obj.desc === undefined || typeof obj.desc === 'string')
            && (obj.visiable_zoom_level === undefined || Number.isInteger(obj.visiable_zoom_level))
            && Number.isInteger(obj.layer)
            && Number.isInteger(obj.x)
            && Number.isInteger(obj.y))
    }

    constructor(obj) { super(obj, ['x', 'y', 'layer']); }

    start_drag() {
        this.sx = this.x;
        this.sy = this.y;
    }

    drag(x, y) {
        this.x = this.sx + x;
        this.y = this.sy + y;
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

    bboxSumDiff() {
        return {
            minSum: this.x + this.y,
            minDiff: this.x - this.y - 1,
            maxSum: this.x + this.y + 2,
            maxDiff: this.x - this.y + 1
        };
    }

    hash(options = {}) {
        const keys = this.commonHash(['point'], options);
        keys.push(this.x, this.y);
        return keys.join(':');
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
            && (obj.visiable_zoom_level === undefined || Number.isInteger(obj.visiable_zoom_level))
            && Number.isInteger(obj.layer)
            && Area.validRects(obj.rects));
    }
    constructor(obj) { super(obj, ['layer', 'rects']); }

    start_drag() {
        let idx = this.selected_index;
        if (idx < 0 || idx >= this.rects.length) {
            idx = 0;
        }
        this.sx = this.rects[idx].x;
        this.sy = this.rects[idx].y;
        this.sw = this.rects[idx].width;
        this.sh = this.rects[idx].height;
    }

    drag(x, y) {
        let idx = this.selected_index;
        if (idx < 0 || idx >= this.rects.length) {
            idx = 0;
        }
        const r = this.rects[idx];
        const dx = this.sx + x - r.x;
        const dy = this.sy + y - r.y;
        if (this.selected_index < 0) {
            for (const rect of this.rects) {
                rect.x += dx;
                rect.y += dy;
            }
        } else {
            r.x += dx;
            r.y += dy;
        }
    }

    resize(x, y) {
        if (this.selected_index < 0 || this.selected_index >= this.rects.length) {
            return;
        }
        const r = this.rects[this.selected_index];
        if (x < 0) {
            r.x = this.sx + x;
            r.width = this.sw - x;
        } else {
            r.x = this.sx;
            r.width = this.sw + x;
        }
        if (y < 0) {
            r.y = this.sy + y;
            r.height = this.sh - y;
        } else {
            r.y = this.sy;
            r.height = this.sh + y;
        }
        return;
    }

    update(obj) {
        if (!Area.validObject(obj)) {
            if (!obj.invalid) this.layer = obj.layer;
            this.name = obj.name;
            this.desc = obj.desc;
            this.visiable_zoom_level = obj.visiable_zoom_level;
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

    append(obj) {
        if (Area.validRects(obj.rects)) {
            this.rects.push(obj.rects[0]);
            this.selected_index = this.rects.length - 1;
        }
    }

    removeSelectedRect() {
        if (this.rects.length == 1) {
            return 'remove'; // remove the area
        }
        if (this.selected_index < 0 || this.selected_index >= this.rects.length) {
            return 'nochange'; // no selected rect, keep the area
        }
        this.rects.splice(this.selected_index, 1);
        return 'keep'; // keep rest of the area
    }

    text() {
        return `(${this.rects[0].x}, ${this.rects[0].y} L ${this.layer}, ${this.rects[0].width}x${this.rects[0].height})`;
    }

    center(idx = -1) {
        if (idx < 0 || idx >= this.rects.length) {
            const { minX, minY, maxX, maxY } = this.bbox();
            const x = (minX + maxX) / 2;
            const y = (minY + maxY) / 2;
            return [x, y];
        } else {
            const r = this.rects[idx];
            const x = r.x + r.width / 2;
            const y = r.y + r.height / 2;
            return [x, y];
        }
    }

    bbox() {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const r of this.rects) {
            if (r.x < minX) minX = r.x;
            if (r.y < minY) minY = r.y;
            if (r.x + r.width > maxX) maxX = r.x + r.width;
            if (r.y + r.height > maxY) maxY = r.y + r.height;
        }
        return { minX, minY, maxX, maxY };
    }

    bboxSumDiff() {
        let minSum = Infinity, minDiff = Infinity, maxSum = -Infinity, maxDiff = -Infinity;
        for (const r of this.rects) {
            const currentMinSum = r.x + r.y;
            const currentMaxSum = r.x + r.width + r.y + r.height;
            const currentMinDiff = r.x - r.y - r.height;
            const currentMaxDiff = r.x + r.width - r.y;
            if (currentMinSum < minSum) minSum = currentMinSum;
            if (currentMinDiff < minDiff) minDiff = currentMinDiff;
            if (currentMaxSum > maxSum) maxSum = currentMaxSum;
            if (currentMaxDiff > maxDiff) maxDiff = currentMaxDiff;
        }
        return { minSum, minDiff, maxSum, maxDiff };
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
        return [cx, cy];
    }

    top() {
        let minX = Infinity, minY = Infinity;
        for (const r of this.rects) {
            if (r.x < minX || (r.x === minX && r.y < minY)) {
                minX = r.x;
                minY = r.y;
            }
        }
        return [minX, minY];
    }

    hash(options = {}) {
        const keys = this.commonHash(['area'], options);
        for (const r of this.rects) {
            keys.push(r.x, r.y, r.width, r.height);
        }
        return keys.join(':');
    }

    parts(options = {}) {
        const allParts = [];
        for (const r of this.rects) {
            allParts.push({ shape: 'rect', x: r.x, y: r.y, width: r.width, height: r.height });
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

export const types = {
    point: Point,
    area: Area
};