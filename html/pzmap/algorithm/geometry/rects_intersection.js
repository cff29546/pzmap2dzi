import { BTree } from '../btree/aux_btree.js';
import { cmpArray } from '../common.js';

function intersect(r1, r2) {
    const xmin = Math.max(r1.x, r2.x);
    const xmax = Math.min(r1.x + r1.width, r2.x + r2.width);
    const ymin = Math.max(r1.y, r2.y);
    const ymax = Math.min(r1.y + r1.height, r2.y + r2.height);
    return (xmin <= xmax && ymin <= ymax);
}

function intersectNC(r1, r2) {
    // Intersection check, not including corner only intersections.
    const xmin = Math.max(r1.x, r2.x);
    const xmax = Math.min(r1.x + r1.width, r2.x + r2.width);
    const ymin = Math.max(r1.y, r2.y);
    const ymax = Math.min(r1.y + r1.height, r2.y + r2.height);
    return (xmin < xmax && ymin < ymax) || (xmin == xmax && ymin < ymax) || (xmin < xmax && ymin == ymax);
}

export function getNeighboursN2(rects, options = {}) {
    // naive O(n^2) approach.
    const { noCorner = false } = options;
    const check = noCorner ? intersectNC : intersect;

    const neighbours = rects.map(() => []);
    for (let i = 0; i < rects.length; i++) {
        for (let j = i + 1; j < rects.length; j++) {
            if (check(rects[i], rects[j])) {
                neighbours[i].push(j);
                neighbours[j].push(i);
            }
        }
    }
    return neighbours;
}

function buildEvents(rects, options = {}) {
    const { axis = 'xy', endFirst = false } = options;
    const x = axis.includes('x');
    const y = axis.includes('y');
    const events = { x: [], y: [], xcost: Infinity, ycost: Infinity };
    // if endFirst is true, the end event comes first in the sorted order.
    const start = endFirst ? 1 : 0;
    const end = endFirst ? 0 : 1;
    for (let i = 0; i < rects.length; i++) {
        const r = rects[i];
        // Event: [position, type, index]
        if (x) {
            events.x.push([r.x, start, i]);
            events.x.push([r.x + r.width, end, i]);
        }
        if (y) {
            events.y.push([r.y, start, i]);
            events.y.push([r.y + r.height, end, i]);
        }
    }
    if (x) {
        events.x.sort(cmpArray);
        events.xcost = 0;
    }
    if (y) {
        events.y.sort(cmpArray);
        events.ycost = 0;
    }
    if (!x || !y) return events;

    for (const ax of ['x', 'y']) {
        let active = 0;
        let cost = 0;
        for (const event of events[ax]) {
            if (event[1] === 0) { // type == start
                cost += active;
                active++;
            } else { // end
                active--;
            }
        }
        events[ax + 'cost'] = cost;
    }

    return events;
}

export function getNeighboursN2Opt(rects, options = {}) {
    // Optimized O(n^2) approach.
    // Select the axis with the least number of intersection checks.
    const { axis = 'xy', noCorner = false } = options;
    if (axis !== 'xy' && axis !== 'x' && axis !== 'y') {
        throw new Error('Invalid axis option. Use "xy", "x", or "y".');
    }
    const check = noCorner ? intersectNC : intersect;
    const neighbours = rects.map(() => []);
    const axisEvents = buildEvents(rects, { axis: axis }); // start first

    const events = (axisEvents.xcost > axisEvents.ycost) ? axisEvents.y : axisEvents.x;
    const active = new Set();
    for (const [pos, type, index] of events) {
        if (type === 0) { // start
            for (const j of active) {
                if (check(rects[index], rects[j])) {
                    neighbours[index].push(j);
                    neighbours[j].push(index);
                }
            }
            active.add(index);
        } else { // end
            active.delete(index);
        }
    }

    return neighbours;
}

function aux(node) {
    // node: [start, end, index]
    if (!node) return -Infinity;

    let max = -Infinity;
    let min = +Infinity;
    const slots = node.slots;
    for (let i = 0; i < slots.length; i++) {
        const slot = slots[i];
        if (i & 1) {
            max = Math.max(max, slot[1]); // end of the interval
            min = Math.min(min, slot[0]); // start of the interval
        } else {
            if (slot) {
                max = Math.max(max, slot.max);
                min = Math.min(min, slot.min);
            }
        }
    }
    if (node.max !== max || node.min !== min) {
        node.max = max;
        node.min = min;
        return true;
    } else {
        return false;
    }
}

function segmentIntersection(a, b) {
    return (a[0] <= b[1] && a[1] >= b[0]);
}

function segmentIntersectionNC(a, b) {
    return (a[0] < b[1] && a[1] > b[0]);
}

function searchIntersection(tree, item) {
    // item: [start, end, index]
    const nodes = [tree.root];
    const result = [];
    const border_result = [];
    while (nodes.length) {
        const node = nodes.pop();
        if (!node) continue;
        const aux = [node.min, node.max];
        if (!segmentIntersection(aux, item)) continue;
        for (let i = 0; i < node.slots.length; i++) {
            if (i & 1) {
                if (segmentIntersectionNC(node.slots[i], item)) {
                    result.push(node.slots[i][2]); // index
                } else if (segmentIntersection(node.slots[i], item)) {
                    border_result.push(node.slots[i][2]); // index
                }
            } else {
                const slot = node.slots[i];
                nodes.push(slot);
            }
        }
    }
    return [result, border_result];
}

export function getNeighboursSweepLine(rects, options = {}) {
    // Sweep line algorithm with a balanced segment tree.
    // This algorithm has O(m log n) complexity.
    // Where n = rects.length and m = number of intersections.
    // Reference: https://www.cs.princeton.edu/courses/archive/fall05/cos226/lectures/geosearch.pdf
    const {btreeOrder = 6, noCorner = false} = options;
    const active = new BTree(btreeOrder, cmpArray, null, aux);
    const neighbours = rects.map(() => []);
    const events = buildEvents(rects, { axis: 'x', endFirst: true }).x; // end events first
    let lastPos = -Infinity;
    const ending = new Set();
    for (const [pos, type, index] of events) {
        // node: [start, end, index]
        if (pos !== lastPos) {
            // Remove node only when pos advances.
            // Keep the ending set for checking corner intersections.
            lastPos = pos;
            for (const i of ending) {
                const r = rects[i];
                const node = [r.y, r.y + r.height, i];
                active.delete(node);
            }
            ending.clear();
        }
        if (type === 1) { // start
            const r = rects[index];
            const node = [r.y, r.y + r.height, index];
            const [res, border_res] = searchIntersection(active, node);
            for (const i of res) {
                neighbours[index].push(i);
                neighbours[i].push(index);
            }
            for (const i of border_res) {
                // border + ending == corner intersection
                if (!(noCorner && ending.has(i))) {
                    neighbours[index].push(i);
                    neighbours[i].push(index);
                }
            }
            active.insert(node);
        } else { // end
            ending.add(index);
        }
    }
    return neighbours;
}

function mergeSegments(segs) {
    const result = [];
    let current = null;
    segs.sort(cmpArray);
    for (const seg of segs) {
        if (current === null) {
            current = seg;
            continue;
        }
        if (seg[0] <= current[1]) {
            current[1] = Math.max(seg[1], current[1]);
        } else {
            result.push(current);
            current = seg;
        }
    }
    if (current !== null) {
        result.push(current);
    }
    return result;
}

function toRatio(value, start, length) {
    if (length <= 0) {
        return 0;
    }
    value = Math.max(value - start, 0);
    return Math.min(1.0, value / length);
}

function convertSegmentsToRatio(segments, start, length) {
    const result = [];
    for (const s of segments) {
        const y0 = toRatio(s[0], start, length);
        const y1 = toRatio(s[1], start, length);
        if (y1 > y0) {
            result.push([y0, y1]);
        }
    }
    return result;
}

export function calcBorder(rect, neighbours) {
    const top = [], bottom = [], left = [], right = [];
    for (const r of neighbours) {
        const y0 = Math.max(rect.y, r.y);
        const y1 = Math.min(rect.y + rect.height, r.y + r.height);
        const x0 = Math.max(rect.x, r.x);
        const x1 = Math.min(rect.x + rect.width, r.x + r.width);
        if (y0 < y1) {
            if (r.x < rect.x && r.x + r.width >= rect.x) {
                left.push([y0, y1]);
            } 
            if (r.x <= rect.x + rect.width && r.x + r.width > rect.x + rect.width) {
                right.push([y0, y1]);
            } 
        }
        if (x0 < x1) {
            if (r.y < rect.y && r.y + r.height >= rect.y) {
                top.push([x0, x1]);
            } 
            if (r.y <= rect.y + rect.height && r.y + r.height > rect.y + rect.height) {
                bottom.push([x0, x1]);
            } 
        }
    }
    return {
        left: convertSegmentsToRatio(mergeSegments(left), rect.y, rect.height),
        right: convertSegmentsToRatio(mergeSegments(right), rect.y, rect.height),
        top: convertSegmentsToRatio(mergeSegments(top), rect.x, rect.width),
        bottom: convertSegmentsToRatio(mergeSegments(bottom), rect.x, rect.width)
    };
}

export function getNeighbours(rects, options = {}) {
    if (rects.length < 100) {
        return getNeighboursN2(rects, options);
    }
    if (rects.length < 1000) {
        return getNeighboursN2Opt(rects, options);
    }
    return getNeighboursSweepLine(rects, options);
}
