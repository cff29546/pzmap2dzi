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
        // if not set, visible_zoom_level is set to 0 (visible at all zoom levels)
        visible_zoom_level: 0,

        // control if the mark is interactive
        // if true, the mark is not clickable and draggable
        // this is usually used for overlays such as 'room' and 'objects'
        passthrough: false,

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
        text_position: 'center',
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
                if (key !== 'id' && obj[key] !== undefined) {
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
            isDiffSum: this.isDiffSum,
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
            return [(cx + cy) / 2, (cx - cy) / 2];
        } else {
            return [cx, cy];
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

export const types = {
    point: Point,
    area: Area
};