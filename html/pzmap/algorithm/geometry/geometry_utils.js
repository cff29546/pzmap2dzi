export function pointInRect(p, rect) {
    return p.x >= rect.x && p.x < rect.x + rect.width && p.y >= rect.y && p.y < rect.y + rect.height;
}

export function pointInPolygon(p, polygon) {
    const { points, masks = [] } = polygon;

    let rayHits = 0;

    const loops = [points, ...masks];
    for (const pts of loops) {
        for (let i = 0; i < pts.length; i++) {
            const a = i ? pts[i - 1] : pts[pts.length - 1];
            const b = pts[i];
            if (a.x === b.x) continue; // vertical edge
            if (p.x < Math.min(a.x, b.x)) continue; // point is to the left of the edge
            if (p.x >= Math.max(a.x, b.x)) continue; // point is to the right of the edge
            const y = a.y + (b.y - a.y) * (p.x - a.x) / (b.x - a.x);
            if (p.y < y) rayHits++;
        }
    }

    return rayHits & 1;
}

// TODO: validate AI code
export function lineClip(x0, y0, x1, y1, xmin, ymin, xmax, ymax) {
    // Liang-Barsky line clipping algorithm
    const dx = x1 - x0;
    const dy = y1 - y0;

    const p = [-dx, dx, -dy, dy];
    const q = [x0 - xmin, xmax - x0, y0 - ymin, ymax - y0];

    let t0 = 0;
    let t1 = 1;

    for (let i = 0; i < 4; i++) {
        if (p[i] === 0) {
            if (q[i] < 0) {
                // Parallel line is outside the clipping rectangle
                return null;
            }
        } else {
            const r = q[i] / p[i];
            if (p[i] < 0) {
                t0 = Math.max(t0, r);
            } else if (p[i] > 0) {
                t1 = Math.min(t1, r);
            }
        }
    }

    if (t0 > t1) {
        // Line is outside the clipping rectangle
        return null;
    }

    // Return the clipped segment coordinates
    return [
        x0 + t0 * dx,
        y0 + t0 * dy,
        x0 + t1 * dx,
        y0 + t1 * dy
    ];
}

function dot(a, b) {
    return a.x * b.x + a.y * b.y;
}

function vec(a, b) {
    return { x: b.x - a.x, y: b.y - a.y };
}

function scale(v, s) {
    return { x: v.x * s, y: v.y * s };
}

function add(v1, v2) {
    return { x: v1.x + v2.x, y: v1.y + v2.y };
}

function dist2(a, b) {
    const v = vec(a, b);
    return dot(v, v);
}

function point2segDist(p, a, b) {
    const ap = vec(a, p);
    const ab = vec(a, b);
    const ab2 = dot(ab, ab);
    const ap_ab = dot(ap, ab);
    const t = Math.max(0, Math.min(1, ap_ab / ab2));
    const pmin = add(a, scale(ab, t));
    const d2 = dist2(p, pmin);
    return [pmin, d2];
}

function closestPointOnPolyline(points, target) {
    // Find the point in the polyline that is closest to the center of the range
    if (points.length === 0) return null;
    if (points.length === 1) return [points[0].x, points[0].y];

    let minPoint = null;
    let minDist = Infinity;
    for (let i = 1; i < points.length; i++) {
        const [pmin, dist2] = point2segDist(target, points[i - 1], points[i]);
        if (dist2 < minDist) {
            minDist = dist2;
            minPoint = pmin;
        }
    }

    return minPoint ? [minPoint.x, minPoint.y] : null;
}

export function polylineLabelPos(points, range) {
    // step1: loop over polyline segments, check its visible range, filter non-visible segments
    // step2: find the longest visible segment
    // step3: return the middle point of the longest visible segment
    if (points.length === 0) return null;
    let bestClipped = null;
    let bestLength = -1;
    for (let i = 1; i < points.length; i++) {
        const a = points[i - 1];
        const b = points[i];
        const clipped = range.segmentClip(a.x, a.y, b.x, b.y);
        if (clipped) {
            const [x0, y0, x1, y1] = clipped;
            const [p1, p2] = [ { x: x0, y: y0 }, { x: x1, y: y1 } ];
            const length = dist2(p1, p2);
            if (length > bestLength) {
                bestLength = length;
                bestClipped = [p1, p2];
            }
        }
    }
    if (!bestClipped) return null; // no visible segment
    const [p1, p2] = bestClipped;
    const dy = p2.y - p1.y;
    const dx = p2.x - p1.x;
    return [(p1.x + p2.x) / 2, (p1.y + p2.y) / 2, [dx, dy]];
}