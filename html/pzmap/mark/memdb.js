import { RTree, validate } from "../algorithm/rtree/rtree.js";

// naive index
class NoIndex {
    constructor(options = {}) {
        this.ids = new Set();
    }

    insert(mark) {
        this.ids.add(mark.id);
    }

    remove(mark) {
        this.ids.delete(mark.id);
    }

    query(data, range, output = null) {
        if (!output) output = [];
        for (const id of this.ids) {
            const mark = data[id];
            if (isInRange(mark, range)) {
                output.push(mark);
            }
        }
        return output;
    }
}

class GridIndex {
    constructor(options = {}) {
        const { gridSize = 256 } = options;
        this.gridSize = gridSize;
        this.grid = {};
    }

    insert(mark) {
        const { minX, minY, maxX, maxY } = mark.bbox();
        const minGridX = Math.floor(minX / this.gridSize);
        const minGridY = Math.floor(minY / this.gridSize);
        const maxGridX = Math.floor(maxX / this.gridSize);
        const maxGridY = Math.floor(maxY / this.gridSize);
        for (let x = minGridX; x <= maxGridX; x++) {
            for (let y = minGridY; y <= maxGridY; y++) {
                const key = `${x}:${y}`;
                if (!this.grid[key]) {
                    this.grid[key] = new Set();
                }
                this.grid[key].add(mark.id);
            }
        }
    }

    remove(mark) {
        const { minX, minY, maxX, maxY } = mark.bbox();
        const minGridX = Math.floor(minX / this.gridSize);
        const minGridY = Math.floor(minY / this.gridSize);
        const maxGridX = Math.floor(maxX / this.gridSize);
        const maxGridY = Math.floor(maxY / this.gridSize);
        for (let x = minGridX; x <= maxGridX; x++) {
            for (let y = minGridY; y <= maxGridY; y++) {
                const key = `${x}:${y}`;
                const g = this.grid[key]
                if (g) {
                    delete this.grid[key][id];
                    g.delete(mark.id);
                    if (g.size === 0) {
                        delete this.grid[key]; // clean up empty grid cells
                    }
                }
            }
        }
    }

    query(data, range, output = null) {
        if (!output) output = [];
        const { minX, minY, maxX, maxY } = range;
        const minGridX = Math.floor(minX / this.gridSize);
        const minGridY = Math.floor(minY / this.gridSize);
        const maxGridX = Math.floor(maxX / this.gridSize);
        const maxGridY = Math.floor(maxY / this.gridSize);
        for (let x = minGridX; x <= maxGridX; x++) {
            for (let y = minGridY; y <= maxGridY; y++) {
                const key = `${x}:${y}`;
                const g = this.grid[key];
                if (g) {
                    for (const id of g) {
                        const mark = data[id];
                        if (isInRange(mark, range)) {
                            output.push(mark);
                        }
                    }
                }
            }
        }
        return output;
    }
}

class RTreeIndex {
    constructor(options = {}) {
        const {
            mode = 'top',
            maxEntries = 9,
            minEntries = 4,
            dimensions = 2,
            strategy = {}
        } = options;
        this.rtreeOptions = { maxEntries, minEntries, dimensions, strategy };
        this.index = {};
        this.mode = mode; // 'top' or 'iso'
        this.index[this.mode] = new RTree(this.rtreeOptions);
    }

    _toItem(mark) {
        const item = { I: mark.id };
        if (this.mode === 'top') {
            const bbox = mark.bbox();
            item.L = [bbox.minX, bbox.minY];
            item.U = [bbox.maxX, bbox.maxY];
        } else {
            const bbox = mark.bboxDiffSum();
            item.L = [bbox.minDiff, bbox.minSum];
            item.U = [bbox.maxDiff, bbox.maxSum];
        }

        return item;
    }

    _clearOtherModeIndex() {
        if (this.mode === 'top') {
            this.index.iso = null;
        } else {
            this.index.top = null;
        }
    }

    insert(mark) {
        const item = this._toItem(mark);
        this.index[this.mode].insert(item);
        this._clearOtherModeIndex();
    }

    remove(mark) {
        if (mark) {
            const item = this._toItem(mark);
            this.index[this.mode].delete(item);
            this._clearOtherModeIndex();
        }
    }

    query(data, range, output = null) {
        if (!output) output = [];
        const bbox = {};
        if (this.mode === 'top') {
            const { minX, minY, maxX, maxY } = range;
            bbox.L = [minX, minY];
            bbox.U = [maxX, maxY];
        } else {
            const { minDiff, maxDiff, minSum, maxSum } = range;
            bbox.L = [minDiff, minSum];
            bbox.U = [maxDiff, maxSum];
        }
        const items = this.index[this.mode].query(bbox);
        for (const item of items) {
            const mark = data[item.I];
            if (mark) {
                output.push(mark);
            }
        }
        return output;
    }

    batchInsert(marks) {
        const items = [];
        for (const mark of marks) {
            items.push(this._toItem(mark));
        }
        this.index[this.mode].batchInsert(items);
        this._clearOtherModeIndex();
    }

    changeMode(data, mode) {
        if (mode !== 'top' && mode !== 'iso') return;
        if (this.mode === mode) return; // no change needed
        if (this.index[mode]) {
            this.mode = mode;
            return; // reuse existing index
        }
        const marks = this.index[this.mode].items().map(item => data[item.I]);
        this.index[mode] = new RTree(this.rtreeOptions);
        this.mode = mode;
        this.batchInsert(marks); // reinsert all marks
    }

    load(marks, index) {
        if (!index[this.mode]) {
            this.batchInsert(marks);
        }
        if (index.top) {
            this.index.top = new RTree(this.rtreeOptions);
            this.index.top.load(index.top);
            if (!validate(this.index.top)) {
                this.index.top = null;
            }
        }
        if (index.iso) {
            this.index.iso = new RTree(this.rtreeOptions);
            this.index.iso.load(index.iso);
            if (!validate(this.index.iso)) {
                this.index.iso = null;
            }
        }
        if (!this.index[this.mode]) {
            this.index[this.mode] = new RTree(this.rtreeOptions);
            this.batchInsert(marks);
        }
    }
}

var INDEX = {
    none: NoIndex,
    grid: GridIndex,
    rtree: RTreeIndex
};

function isInRange(mark, range) {
    if (range.diffSum) {
        return isInDiffSumRange(mark, range);
    } else {
        return isInXYRange(mark, range);
    }
}

function isInXYRange(mark, range) {
    const { minX, minY, maxX, maxY } = mark.bbox();
    const xmin = minX > range.minX ? minX : range.minX;
    const xmax = maxX < range.maxX ? maxX : range.maxX;
    const ymin = minY > range.minY ? minY : range.minY;
    const ymax = maxY < range.maxY ? maxY : range.maxY;
    return (xmin <= xmax && ymin <= ymax);
}

function isInDiffSumRange(mark, range) {
    // diff-sum range for iso view
    const { minDiff, maxDiff, minSum, maxSum } = mark.bboxDiffSum();
    const dmin = minDiff > range.minDiff ? minDiff : range.minDiff;
    const dmax = maxDiff < range.maxDiff ? maxDiff : range.maxDiff;
    const smin = minSum > range.minSum ? minSum : range.minSum;
    const smax = maxSum < range.maxSum ? maxSum : range.maxSum;
    return (smin <= smax && dmin <= dmax);
}

export class MarkDatabase {
    constructor(mode = 'top', useLayerFilter = false, indexType = null, indexOptions = {}) {
        this.mode = mode; // 'top' or 'iso'
        this.marks = {};
        this.useLayerFilter = useLayerFilter;
        this.index = {};
        this.indexType = INDEX[indexType] || NoIndex;
        this.indexOptions = indexOptions;
    }

    _indexKey(layer, zoomLevel) {
        return this.useLayerFilter ? `${layer}:${zoomLevel}` : `0:${zoomLevel}`;
    }

    _getIndex(key) {
        if (!this.index[key]) {
            const options = { mode: this.mode };
            Object.assign(options, this.indexOptions);
            this.index[key] = new this.indexType(options);
        }
        return this.index[key];
    }

    _index(layer, zoomLevel) {
        return this._getIndex(this._indexKey(layer, zoomLevel));
    }

    _removeFromIndex(mark) {
        const oldMark = this.marks[mark.id];
        if (oldMark) {
            const index = this._index(oldMark.layer || 0, oldMark.visible_zoom_level || 0);
            index.remove(oldMark);
        }
    }

    upsert(mark, range = null, updateIndex = true) {
        this._removeFromIndex(mark);
        this.marks[mark.id] = mark;
        if (updateIndex) {
            const index = this._index(mark.layer || 0, mark.visible_zoom_level || 0);
            index.insert(mark);
        }
        if (range && !isInRange(mark, range)) {
            return false; // mark not in visible range
        }
        return true; // mark in visible range
    }

    batchInsert(marks, range = null, indexes = null) {
        const batch = {};
        let inRange = false;
        for (const mark of marks) {
            const markInRange = this.upsert(mark, range, false);
            inRange = markInRange || inRange;
            const indexKey = this._indexKey(mark.layer || 0, mark.visible_zoom_level || 0);
            if (!batch[indexKey]) {
                batch[indexKey] = [];
            }
            batch[indexKey].push(mark);
        }
        for (const [indexKey, marks] of Object.entries(batch)) {
            if (indexes && indexes[indexKey]) {
                // load pre-existing index
                const { type, options, index } = indexes[indexKey];
                if (INDEX[type]) {
                    const loadIndex = new INDEX[type](options);
                    if (loadIndex.load) {
                        loadIndex.load(marks, index);
                        this.index[indexKey] = loadIndex;
                        continue;
                    }
                }
            }
            const index = this._getIndex(indexKey);
            if (index.batchInsert) {
                index.batchInsert(marks);
            } else {
                for (const mark of marks) {
                    index.insert(mark);
                }
            }
        }
        return inRange;
    }

    clear() {
        this.marks = {};
        this.index = {};
    }

    remove(id) {
        const mark = this.marks[id];
        if (!mark) return;
        delete this.marks[id];
        const index = this._index(mark.layer || 0, mark.visible_zoom_level || 0);
        index.remove(mark);
    }

    has(id) {
        return this.marks.hasOwnProperty(id);
    }

    get(id, range = null) {
        const mark = this.marks[id];
        if (!mark) return null;
        if (range && !isInRange(mark, range)) return null;
        return mark;
    }

    all() {
        return Object.values(this.marks);
    }

    query(range, layer = 0, zoomLevel = null) {
        if (!zoomLevel) {
            zoomLevel = 0;
        }
        const result = [];
        for (let zoom = 0; zoom <= zoomLevel; zoom++) {
            const index = this._index(layer, zoom);
            index.query(this.marks, range, result);
        }
        return result;
    }

    changeMode(mode) {
        if (this.mode === mode) return; // no change needed
        this.mode = mode;
        for (const index of Object.values(this.index)) {
            if (index.changeMode) {
                index.changeMode(this.marks, mode);
            }
        }
    }
}