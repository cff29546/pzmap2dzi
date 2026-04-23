import {
    getNeighboursN2,
    getNeighboursSweepLine
} from '../geometry/rects_intersection.js';

function sortNeighbours(neighbours) {
    return neighbours.map(list => [...list].sort((a, b) => a - b));
}

function equalNeighbours(a, b) {
    const sa = sortNeighbours(a);
    const sb = sortNeighbours(b);
    if (sa.length !== sb.length) return false;
    for (let i = 0; i < sa.length; i++) {
        if (sa[i].length !== sb[i].length) return false;
        for (let j = 0; j < sa[i].length; j++) {
            if (sa[i][j] !== sb[i][j]) return false;
        }
    }
    return true;
}

function firstDiff(a, b) {
    const sa = sortNeighbours(a);
    const sb = sortNeighbours(b);
    for (let i = 0; i < Math.min(sa.length, sb.length); i++) {
        if (sa[i].length !== sb[i].length) {
            return { i, a: sa[i], b: sb[i] };
        }
        for (let j = 0; j < sa[i].length; j++) {
            if (sa[i][j] !== sb[i][j]) {
                return { i, a: sa[i], b: sb[i] };
            }
        }
    }
    if (sa.length !== sb.length) {
        return { i: Math.min(sa.length, sb.length), a: sa.at(-1), b: sb.at(-1) };
    }
    return null;
}

function makeRng(seed = 1) {
    let s = seed >>> 0;
    return () => {
        s = (1664525 * s + 1013904223) >>> 0;
        return s / 0x100000000;
    };
}

function randomRects(count, coordRange, sizeRange, seed) {
    const rand = makeRng(seed);
    const rects = [];
    for (let i = 0; i < count; i++) {
        rects.push({
            x: Math.floor(rand() * coordRange),
            y: Math.floor(rand() * coordRange),
            width: Math.floor(rand() * sizeRange) + 1,
            height: Math.floor(rand() * sizeRange) + 1
        });
    }
    return rects;
}

function mismatch(rects, options) {
    const n2 = getNeighboursN2(rects, options);
    const sw = getNeighboursSweepLine(rects, options);
    return {
        mismatch: !equalNeighbours(n2, sw),
        n2,
        sw,
        diff: firstDiff(n2, sw)
    };
}

function shrinkCase(rects, options) {
    let arr = rects.slice();
    let changed = true;
    while (changed && arr.length > 2) {
        changed = false;
        for (let i = 0; i < arr.length; i++) {
            const cand = arr.slice(0, i).concat(arr.slice(i + 1));
            const m = mismatch(cand, options);
            if (m.mismatch) {
                arr = cand;
                changed = true;
                break;
            }
        }
    }
    return arr;
}

function main() {
    const options = { noEdge: true };

    for (let seed = 1; seed <= 20000; seed++) {
        const rects = randomRects(30, 12, 5, seed);
        const m = mismatch(rects, options);
        if (!m.mismatch) continue;

        const shrunk = shrinkCase(rects, options);
        const m2 = mismatch(shrunk, options);

        console.log('FOUND_FAIL');
        console.log('seed=', seed);
        console.log('count=', rects.length, 'shrunk=', shrunk.length);
        console.log('options=', JSON.stringify(options));
        console.log('firstDiff=', JSON.stringify(m2.diff));
        console.log('rects=', JSON.stringify(shrunk));
        console.log('n2=', JSON.stringify(sortNeighbours(m2.n2)));
        console.log('sw=', JSON.stringify(sortNeighbours(m2.sw)));
        return;
    }

    console.log('NO_FAIL_FOUND');
}

main();
