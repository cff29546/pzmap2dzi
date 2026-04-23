import {
    getNeighboursN2,
    getNeighboursN2Opt,
    getNeighboursSweepLine
} from '../geometry/rects_intersection.js';

function sortNeighbours(neighbours) {
    return neighbours.map(list => [...list].sort((a, b) => a - b));
}

function assertNeighboursEqual(actual, expected, msg) {
    const a = JSON.stringify(sortNeighbours(actual));
    const e = JSON.stringify(sortNeighbours(expected));
    if (a !== e) {
        throw new Error(`${msg}\nexpected: ${e}\nactual:   ${a}`);
    }
}

function assertMethodsAgree(rects, options) {
    const n2 = getNeighboursN2(rects, options);
    const n2opt = getNeighboursN2Opt(rects, options);
    const sweep = getNeighboursSweepLine(rects, options);

    assertNeighboursEqual(n2opt, n2, `N2Opt mismatch for options=${JSON.stringify(options)}`);
    assertNeighboursEqual(sweep, n2, `Sweep mismatch for options=${JSON.stringify(options)}`);
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

Deno.test('rects_intersection mode semantics (edge/corner/area)', () => {
    const rects = [
        { x: 0, y: 0, width: 2, height: 2 }, // 0: base
        { x: 2, y: 0, width: 2, height: 2 }, // 1: edge-only with 0
        { x: 2, y: 2, width: 2, height: 2 }, // 2: corner-only with 0, edge-only with 1
        { x: 1, y: 1, width: 2, height: 2 }, // 3: area overlap with 0,1,2
        { x: 5, y: 5, width: 1, height: 1 }  // 4: disjoint
    ];

    const expectedDefault = [
        [1, 2, 3],
        [0, 2, 3],
        [0, 1, 3],
        [0, 1, 2],
        []
    ];

    const expectedNoCorner = [
        [1, 3],
        [0, 2, 3],
        [1, 3],
        [0, 1, 2],
        []
    ];

    const expectedNoEdge = [
        [2, 3],
        [3],
        [0, 3],
        [0, 1, 2],
        []
    ];

    const expectedNoCornerNoEdge = [
        [3],
        [3],
        [3],
        [0, 1, 2],
        []
    ];

    assertNeighboursEqual(getNeighboursN2(rects), expectedDefault, 'default mode mismatch');
    assertNeighboursEqual(getNeighboursN2(rects, { noCorner: true }), expectedNoCorner, 'noCorner mode mismatch');
    assertNeighboursEqual(getNeighboursN2(rects, { noEdge: true }), expectedNoEdge, 'noEdge mode mismatch');
    assertNeighboursEqual(
        getNeighboursN2(rects, { noCorner: true, noEdge: true }),
        expectedNoCornerNoEdge,
        'noCorner+noEdge mode mismatch'
    );
});

Deno.test('rects_intersection algorithms agree on random fixtures', () => {
    const seed = Math.floor(Math.random() * (1 << 30));
    console.log(`Using seed: ${seed}`);
    const rects = randomRects(300, 80, 12, seed);
    const optionsList = [
        {},
        { noCorner: true },
        { noEdge: true },
        { noCorner: true, noEdge: true }
    ];

    for (const options of optionsList) {
        assertMethodsAgree(rects, options);
    }
});
