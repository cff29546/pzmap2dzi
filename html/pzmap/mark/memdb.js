import { RTree } from "../algorithm/rtree/rtree.js";

// naive index
class NoIndex {
    constructor(options = {}) {
        this.data = {};
    }

    insert(mark) {
        this.data[mark.id] = mark;
    }

    remove(mark) {
        delete this.data[mark.id];
    }

    query(range) {
        // Naive implementation, should be replaced with a proper R-tree query
        return Object.values(this.data).filter(mark => isInXYRange(mark, range));
    }
}

class GridIndex {
    constructor(options = {}) {
        const { gridSize = 256 } = options;
        this.gridSize = gridSize;
        this.grid = {};
    }

    insert(mark) {
        const id = mark.id;
        const { minX, minY, maxX, maxY } = mark.bbox();
        const minGridX = Math.floor(minX / this.gridSize);
        const minGridY = Math.floor(minY / this.gridSize);
        const maxGridX = Math.floor(maxX / this.gridSize);
        const maxGridY = Math.floor(maxY / this.gridSize);
        for (let x = minGridX; x <= maxGridX; x++) {
            for (let y = minGridY; y <= maxGridY; y++) {
                const key = `${x}:${y}`;
                if (!this.grid[key]) {
                    this.grid[key] = {};
                }
                this.grid[key][id] = mark;
            }
        }
    }

    remove(mark) {
        const id = mark.id;
        const { minX, minY, maxX, maxY } = mark.bbox();
        const minGridX = Math.floor(minX / this.gridSize);
        const minGridY = Math.floor(minY / this.gridSize);
        const maxGridX = Math.floor(maxX / this.gridSize);
        const maxGridY = Math.floor(maxY / this.gridSize);
        for (let x = minGridX; x <= maxGridX; x++) {
            for (let y = minGridY; y <= maxGridY; y++) {
                const key = `${x}:${y}`;
                if (this.grid[key] && this.grid[key][id]) {
                    delete this.grid[key][id];
                    if (Object.keys(this.grid[key]).length === 0) {
                        delete this.grid[key]; // clean up empty grid cells
                    }
                }
            }
        }
    }

    query(range) {
        const result = [];
        const { minX, minY, maxX, maxY } = range;
        const minGridX = Math.floor(minX / this.gridSize);
        const minGridY = Math.floor(minY / this.gridSize);
        const maxGridX = Math.floor(maxX / this.gridSize);
        const maxGridY = Math.floor(maxY / this.gridSize);
        for (let x = minGridX; x <= maxGridX; x++) {
            for (let y = minGridY; y <= maxGridY; y++) {
                const key = `${x}:${y}`;
                if (this.grid[key]) {
                    for (const mark of Object.values(this.grid[key])) {
                        if (isInXYRange(mark, range)) {
                            result.push(mark);
                        }
                    }
                }
            }
        }
        return result;
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
        this.rtree = new RTree({
            maxEntries,
            minEntries,
            dimensions,
            strategy
        });
        this.mode = mode; // 'top' or 'iso'
        this.data = {};
    }

    _toItem(mark) {
        const item = { I: mark.id };
        if (this.mode === 'top') {
            const bbox = mark.bbox();
            item.L = [bbox.minX, bbox.minY];
            item.U = [bbox.maxX, bbox.maxY];
        } else {
            const bbox = mark.bboxSumDiff();
            item.L = [bbox.minSum, bbox.minDiff];
            item.U = [bbox.maxSum, bbox.maxDiff];
        }

        return item;
    }

    insert(mark) {
        const item = this._toItem(mark);
        this.data[mark.id] = [mark, item];
        this.rtree.insert(item);
    }

    remove(mark) {
        const value = this.data[mark.id];
        if (value) {
            const item = value[1];
            this.rtree.delete(item);
            delete this.data[mark.id];
        }
    }

    query(range) {
        const result = [];
        const bbox = {};
        if (this.mode === 'top') {
            const { minX, minY, maxX, maxY } = range;
            bbox.L = [minX, minY];
            bbox.U = [maxX, maxY];
        } else {
            const { minSum, minDiff, maxSum, maxDiff } = range;
            bbox.L = [minSum, minDiff];
            bbox.U = [maxSum, maxDiff];
        }
        const items = this.rtree.query(bbox);
        for (const item of items) {
            const value = this.data[item.I];
            if (value) {
                result.push(value[0]); // push the mark object
            }
        }
        return result;
    }

    batchInsert(marks) {
        const items = [];
        for (const mark of marks) {
            const item = this._toItem(mark);
            this.data[mark.id] = [mark, item];
            items.push(item);
        }
        this.rtree.batchInsert(items);
    }

    changeMode(mode) {
        if (this.mode === mode) return; // no change needed
        this.mode = mode;
        const marks = Object.values(this.data).map(value => value[0]);
        this.rtree.clear(); // clear the current R-tree
        this.data = {}; // reset data
        this.batchInsert(marks); // reinsert all marks
    }
}

var INDEX = {
    none: NoIndex,
    grid: GridIndex,
    rtree: RTreeIndex
};

function isInRange(mark, range) {
    if (range.sumDiff) {
        return isInXYRange(mark, range) && isInSumDiffRange(mark, range);
    }
    return isInXYRange(mark, range);
}

function isInXYRange(mark, range) {
    const { minX, minY, maxX, maxY } = mark.bbox();
    const xmin = Math.max(minX, range.minX);
    const xmax = Math.min(maxX, range.maxX);
    const ymin = Math.max(minY, range.minY);
    const ymax = Math.min(maxY, range.maxY);
    return (xmin <= xmax && ymin <= ymax);
}

function isInSumDiffRange(mark, range) {
    // sum-diff range for iso view
    const { minSum, maxSum, minDiff, maxDiff } = mark.bboxSumDiff();
    const smin = Math.max(minSum, range.minSum);
    const smax = Math.min(maxSum, range.maxSum);
    const dmin = Math.max(minDiff, range.minDiff);
    const dmax = Math.min(maxDiff, range.maxDiff);
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
            const index = this._index(oldMark.layer || 0, oldMark.visiable_zoom_level || 0);
            index.remove(oldMark);
        }
    }

    upsert(mark, range = null, updateIndex = true) {
        this._removeFromIndex(mark);
        this.marks[mark.id] = mark;
        if (updateIndex) {
            const index = this._index(mark.layer || 0, mark.visiable_zoom_level || 0);
            index.insert(mark);
        }
        if (range && !isInRange(mark, range)) {
            return false; // mark not in visiable range
        }
        return true; // mark in visiable range
    }

    batchInsert(marks, range = null) {
        const batch = {};
        let inRange = false;
        for (const mark of marks) {
            const markInRange = this.upsert(mark, range, false);
            inRange = markInRange || inRange;
            const indexKey = this._indexKey(mark.layer || 0, mark.visiable_zoom_level || 0);
            if (!batch[indexKey]) {
                batch[indexKey] = [];
            }
            batch[indexKey].push(mark);
        }
        for (const [indexKey, marks] of Object.entries(batch)) {
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
        const index = this._index(mark.layer || 0, mark.visiable_zoom_level || 0);
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
            const marks = index.query(range);
            for (const mark of marks) {
                if (!range.sumDiff || isInSumDiffRange(mark, range)) {
                    result.push(mark);
                }
            }
        }

        return result;
    }

    changeMode(mode) {
        if (this.mode === mode) return; // no change needed
        this.mode = mode;
        for (const index of Object.values(this.index)) {
            if (index.changeMode) {
                index.changeMode(mode);
            }
        }
    }
}