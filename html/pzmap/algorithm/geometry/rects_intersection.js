import { format } from '../../util.js';
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

function toBound(rect) {
    return {
        x0: rect.x,
        y0: rect.y,
        x1: rect.x + rect.width,
        y1: rect.y + rect.height
    };
}

const lt = (a, b) => a < b;
const lte = (a, b) => a <= b;
function calcMissingBorderSingle(r, n, result, highPriority=true) {
    const cmp = highPriority ? lte : lt;
    const y0 = r.y0 > n.y0 ? r.y0 : n.y0;
    const y1 = r.y1 < n.y1 ? r.y1 : n.y1;
    const x0 = r.x0 > n.x0 ? r.x0 : n.x0;
    const x1 = r.x1 < n.x1 ? r.x1 : n.x1;
    if (y0 < y1) {
        if (cmp(n.x0, r.x0) && r.x0 <= n.x1) {
            result.left.push([y0, y1]);
        }
        if (n.x0 <= r.x1 && cmp(r.x1, n.x1)) {
            result.right.push([y0, y1]);
        }
    }
    if (x0 < x1) {
        if (cmp(n.y0, r.y0) && r.y0 <= n.y1) {
            result.top.push([x0, x1]);
        }
        if (n.y0 <= r.y1 && cmp(r.y1, n.y1)) {
            result.bottom.push([x0, x1]);
        }
    }
}

function calcMissingBorder(rect, neighbourRects, neighbourRectsLowPriority) {
    const result = { top: [], bottom: [], left: [], right: [] };
    const r = toBound(rect);
    for (const n of neighbourRects) {
        calcMissingBorderSingle(r, toBound(n), result, true);
    }
    for (const n of neighbourRectsLowPriority) {
        calcMissingBorderSingle(r, toBound(n), result, false);
    }

    for (const side of ['top', 'bottom', 'left', 'right']) {
        result[side] = mergeSegments(result[side]);
    }
    return result;
}

var AX_MAP = [
    ['top',    'x0', 'x1', (b, s, e) => [{x: s, y: b.y0}, {x: e, y: b.y0}]],
    ['right',  'y0', 'y1', (b, s, e) => [{x: b.x1, y: s}, {x: b.x1, y: e}]],
    ['bottom', 'x0', 'x1', (b, s, e) => [{x: e, y: b.y1}, {x: s, y: b.y1}]],
    ['left',   'y0', 'y1', (b, s, e) => [{x: b.x0, y: e}, {x: b.x0, y: s}]],
];
function calcBorderSegments(rect, neighbourRects, neighbourRectsLowPriority, output=null) {
    const missing = calcMissingBorder(rect, neighbourRects, neighbourRectsLowPriority);
    if (output === null) output = [];
    const corners = [];
    const bound = toBound(rect);
    for (const [side, ax0, ax1, fmt] of AX_MAP) {
        const start = bound[ax0];
        let current = start;
        const end = bound[ax1];
        for (const [s, e] of missing[side]) {
            if (s > current) {
                if (current == start) {
                    corners.push(fmt(bound, current, s));
                } else {
                    output.push(fmt(bound, current, s));
                }
            }
            current = e;
        }
        if (current < end) {
            corners.push(fmt(bound, current, end));
        }
    }
    mergeSegments2D(corners, output);
    return output;
}

function bboxArea(points) {
    if (!points || points.length === 0) return 0;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of points) {
        minX = p.x < minX ? p.x : minX;
        minY = p.y < minY ? p.y : minY;
        maxX = p.x > maxX ? p.x : maxX;
        maxY = p.y > maxY ? p.y : maxY;
    }
    return (maxX - minX) * (maxY - minY);
}

function fmtPoint(p) {
    return p.x + ',' + p.y;
}

export function mergeSegments2D(segs, output=null) {
    if (output === null) output = [];
    const startMap = {};
    for (let i = 0; i < segs.length; i++) {
        const seg = segs[i];
        const start = fmtPoint(seg[0]);
        const end = fmtPoint(seg[seg.length - 1]);
        if (startMap[start] === undefined) {
            startMap[start] = i;
        }
    }
    for (let i = 0; i < segs.length; i++) {
        const seg = segs[i];
        if (seg !== null) {
            let end = fmtPoint(seg[seg.length - 1]);
            let j = startMap[end];
            while (j !== undefined && segs[j] !== null && j !== i) {
                const next = segs[j];
                for (let k = 1; k < next.length; k++) {
                    seg.push(next[k]);
                }
                segs[j] = null;
                end = fmtPoint(seg[seg.length - 1]);
                j = startMap[end];
            }
            if (j === i) {
                segs[i] = null;
                seg.pop();
                output.push(seg);
            }
        }
    }
    for (const seg of segs) {
        if (seg !== null && seg.length > 1) {
            output.push(seg);
        }
    }
    return output;

    for (const p of output) {
        compactPolygon(p);
    }
    let maxArea = -1;
    let maxIndex = -1;
    for (let i = 0; i < output.length; i++) {
        const seg = output[i];
        const area = bboxArea(seg);
        if (area > maxArea) {
            maxArea = area;
            maxIndex = i;
        }
    }
    if (maxIndex >= 0) {
        const maxSeg = output.splice(maxIndex, 1);
        output.push(maxSeg[0]);
    }

    return output;
}

function pointEqual(a, b) {
    return a.x === b.x && a.y === b.y;
}

function compactPolygon(polygon) {
    // Remove adjacent points with same coordinates and remove collinear points (in-place)
    if (!polygon || polygon.length < 2) return;

    // Remove adjacent duplicate points
    while (polygon.length > 1 && pointEqual(polygon[0], polygon[polygon.length - 1])) {
        polygon.pop();
    }
    for (let i = polygon.length - 1; i > 0; i--) {
        const a = polygon[i];
        const b = polygon[i - 1];
        if (pointEqual(a, b)) {
            polygon.splice(i, 1);
        }
    }
    // Remove collinear points
    let i = 0;
    while (polygon.length > 2 && i < polygon.length) {
        const prev = polygon[(i - 1 + polygon.length) % polygon.length];
        const curr = polygon[i];
        const next = polygon[(i + 1) % polygon.length];
        // Check if prev, curr, next are collinear
        const dx1 = curr.x - prev.x;
        const dy1 = curr.y - prev.y;
        const dx2 = next.x - curr.x;
        const dy2 = next.y - curr.y;
        if (dx1 * dy2 + dx2 * dy1 === 0 && dx1 * dx2 + dy1 * dy2 >= 0) {
            polygon.splice(i, 1);
        } else {
            i++;
        }
    }
}

function splitConnectedGroups(rects, neighbours) {
    const groups = [];
    const visited = new Array(rects.length).fill(false);

    for (let i = 0; i < rects.length; i++) {
        if (visited[i]) continue;
        const group = [];
        const stack = [i];
        visited[i] = true;
        while (stack.length) {
            const idx = stack.pop();
            group.push(idx);
            for (const n of neighbours[idx]) {
                if (!visited[n]) {
                    visited[n] = true;
                    stack.push(n);
                }
            }
        }
        groups.push(group);
    }
    return groups;
}

function formatPolygon(segs) {
    if (segs.length === 0) return null;
    for (const seg of segs) {
        compactPolygon(seg);
    }
    let maxArea = -1;
    let maxIndex = -1;
    for (let i = 0; i < segs.length; i++) {
        const area = bboxArea(segs[i]);
        if (area > maxArea) {
            maxArea = area;
            maxIndex = i;
        }
    }
    return { points: segs.splice(maxIndex, 1)[0], masks: segs };
}

export function rectsToPolygons(rects) {
    // polygons: [ polygon1, polygon2, ... ]
    // polygon: {
    //     points: <outer boundary>,
    //     masks: [ <mask1>, <mask2>, ... ] }
    // }
    // mask or outer boundary: [ {x, y}, {x, y}, ... ]
    const neighbours = getNeighbours(rects, { noCorner: true });
    const groups = splitConnectedGroups(rects, neighbours);
    const polygons = [];
    for (const group of groups) {
        const segs = [];
        for (const i of group) {
            const rect = rects[i];
            const neighbourRects = neighbours[i].filter(j => j < i).map(j => rects[j]);
            const neighbourRectsLowPriority = neighbours[i].filter(j => j > i).map(j => rects[j]);
            calcBorderSegments(rect, neighbourRects, neighbourRectsLowPriority, segs);
        }
        const polygon = formatPolygon(mergeSegments2D(segs));
        if (polygon) {
            polygons.push(polygon);
        }
    }
    return polygons;
}

export function calcMissingBorderRatio(rect, neighbourRects, neighbourRectsLowPriority) {
    const missing = calcMissingBorder(rect, neighbourRects, neighbourRectsLowPriority);
    return {
        left: convertSegmentsToRatio(missing.left, rect.y, rect.height),
        right: convertSegmentsToRatio(missing.right, rect.y, rect.height),
        top: convertSegmentsToRatio(missing.top, rect.x, rect.width),
        bottom: convertSegmentsToRatio(missing.bottom, rect.x, rect.width)
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
