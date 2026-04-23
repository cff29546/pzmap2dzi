import { getNeighbours } from './rects_intersection.js';

// TODO: use better algorithm
// There exists a O(n ^ (3/2) log n) algorithm to find the minimum number of rectangles to cover a set of rectangles
// see:
// https://mathoverflow.net/questions/80665/how-to-cover-a-set-in-a-grid-with-as-few-rectangles-as-possible
// https://arxiv.org/abs/0908.3916
// https://ali-ibrahim137.github.io/competitive/programming/2020/01/02/maximum-independent-set-in-bipartite-graphs.html

function rectRight(rect) {
    return rect.x + rect.width;
}

function rectBottom(rect) {
    return rect.y + rect.height;
}

function cellCoveredByRects(x0, y0, x1, y1, rects) {
    for (const rect of rects) {
        if (rect.x < x1 && rectRight(rect) > x0 && rect.y < y1 && rectBottom(rect) > y0) {
            return true;
        }
    }
    return false;
}

function mergeRowsToRects(stripsPerRow, yCoords) {
    const output = [];
    const active = new Map();

    for (let row = 0; row < stripsPerRow.length; row++) {
        const y0 = yCoords[row];
        const y1 = yCoords[row + 1];
        const rowStrips = stripsPerRow[row];
        const currentKeys = new Set();

        for (const strip of rowStrips) {
            const key = strip.x0 + ',' + strip.x1;
            currentKeys.add(key);
            const existing = active.get(key);
            if (existing && existing.y1 === y0) {
                existing.y1 = y1;
            } else {
                active.set(key, {
                    x0: strip.x0,
                    x1: strip.x1,
                    y0,
                    y1
                });
            }
        }

        for (const [key, value] of active.entries()) {
            if (!currentKeys.has(key)) {
                output.push({
                    x: value.x0,
                    y: value.y0,
                    width: value.x1 - value.x0,
                    height: value.y1 - value.y0
                });
                active.delete(key);
            }
        }
    }

    for (const value of active.values()) {
        output.push({
            x: value.x0,
            y: value.y0,
            width: value.x1 - value.x0,
            height: value.y1 - value.y0
        });
    }

    return output;
}

function mergeColsToRects(stripsPerCol, xCoords) {
    const output = [];
    const active = new Map();

    for (let col = 0; col < stripsPerCol.length; col++) {
        const x0 = xCoords[col];
        const x1 = xCoords[col + 1];
        const colStrips = stripsPerCol[col];
        const currentKeys = new Set();

        for (const strip of colStrips) {
            const key = strip.y0 + ',' + strip.y1;
            currentKeys.add(key);
            const existing = active.get(key);
            if (existing && existing.x1 === x0) {
                existing.x1 = x1;
            } else {
                active.set(key, {
                    y0: strip.y0,
                    y1: strip.y1,
                    x0,
                    x1
                });
            }
        }

        for (const [key, value] of active.entries()) {
            if (!currentKeys.has(key)) {
                output.push({
                    x: value.x0,
                    y: value.y0,
                    width: value.x1 - value.x0,
                    height: value.y1 - value.y0
                });
                active.delete(key);
            }
        }
    }

    for (const value of active.values()) {
        output.push({
            x: value.x0,
            y: value.y0,
            width: value.x1 - value.x0,
            height: value.y1 - value.y0
        });
    }

    return output;
}

function buildCoverByRowStrips(rects, xCoords, yCoords) {
    const stripsPerRow = [];
    let stripCount = 0;
    for (let yi = 0; yi < yCoords.length - 1; yi++) {
        const y0 = yCoords[yi];
        const y1 = yCoords[yi + 1];

        const rowStrips = [];
        let runStart = null;
        for (let xi = 0; xi < xCoords.length - 1; xi++) {
            const x0 = xCoords[xi];
            const x1 = xCoords[xi + 1];
            const covered = cellCoveredByRects(x0, y0, x1, y1, rects);
            if (covered) {
                if (runStart === null) {
                    runStart = x0;
                }
            } else if (runStart !== null) {
                rowStrips.push({ x0: runStart, x1: x0 });
                stripCount++;
                runStart = null;
            }
        }
        if (runStart !== null) {
            rowStrips.push({ x0: runStart, x1: xCoords[xCoords.length - 1] });
            stripCount++;
        }
        stripsPerRow.push(rowStrips);
    }
    return {
        stripCount,
        rects: mergeRowsToRects(stripsPerRow, yCoords)
    };
}

function buildCoverByColStrips(rects, xCoords, yCoords) {
    const stripsPerCol = [];
    let stripCount = 0;
    for (let xi = 0; xi < xCoords.length - 1; xi++) {
        const x0 = xCoords[xi];
        const x1 = xCoords[xi + 1];

        const colStrips = [];
        let runStart = null;
        for (let yi = 0; yi < yCoords.length - 1; yi++) {
            const y0 = yCoords[yi];
            const y1 = yCoords[yi + 1];
            const covered = cellCoveredByRects(x0, y0, x1, y1, rects);
            if (covered) {
                if (runStart === null) {
                    runStart = y0;
                }
            } else if (runStart !== null) {
                colStrips.push({ y0: runStart, y1: y0 });
                stripCount++;
                runStart = null;
            }
        }
        if (runStart !== null) {
            colStrips.push({ y0: runStart, y1: yCoords[yCoords.length - 1] });
            stripCount++;
        }
        stripsPerCol.push(colStrips);
    }
    return {
        stripCount,
        rects: mergeColsToRects(stripsPerCol, xCoords)
    };
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

function groupCover(rects) {
    const xSet = new Set();
    const ySet = new Set();
    for (const rect of rects) {
        xSet.add(rect.x);
        xSet.add(rectRight(rect));
        ySet.add(rect.y);
        ySet.add(rectBottom(rect));
    }

    const xCoords = Array.from(xSet).sort((a, b) => a - b);
    const yCoords = Array.from(ySet).sort((a, b) => a - b);

    if (xCoords.length < 2 || yCoords.length < 2) {
        return [];
    }

    const byRow = buildCoverByRowStrips(rects, xCoords, yCoords);
    const byCol = buildCoverByColStrips(rects, xCoords, yCoords);

    if (byCol.stripCount < byRow.stripCount) {
        return byCol.rects;
    }
    if (byCol.stripCount > byRow.stripCount) {
        return byRow.rects;
    }
    return byCol.rects.length < byRow.rects.length ? byCol.rects : byRow.rects;
}

export function rectsToRectCover(inputRects) {
    const rects = inputRects.filter(rect => rect.width > 0 && rect.height > 0);

    if (rects.length === 0) {
        return [];
    }

    const neighbours = getNeighbours(rects, { noCorner: true });
    const groups = splitConnectedGroups(rects, neighbours);
    const output = [];

    for (const group of groups) {
        if (group.length < 2) {
            output.push(rects[group[0]]);
            continue;
        }
        const groupRects = group.map(i => rects[i]);
        output.push(...groupCover(groupRects));
    }

    return output;
}
