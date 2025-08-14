import * as Node from './node.js';

// BulkLoad(entries, m, M, dim) -> root
// This function builds an R-tree from a set of items or entries (of the same level) using the bulk loading method.

// PR-tree (Priority R-tree 2004)
// Modified version, internal nodes only have 2 priority leaves of the splitting axis
export function prTree(entries, m, M, dim) {
    if (entries.length === 0) {
        return null;
    }

    let E = entries.slice(); // copy
    while (E.length > 1 || Node.isItem(E[0])) {
        E = pseudoPRSplit(E, m, M, dim);
    }

    return E[0];
}

function pseudoPRSplit(E, m, M, dim, dir = 0) {
    if (E.length === 0) {
        return [];
    }
    if (E.length <= M) {
        return [Node.createByEntries(E)];
    }
    const ax = dir % dim;
    if (dir < dim) {
        E.sort((a, b) => a.L[ax] - b.L[ax]);
    } else {
        E.sort((a, b) => a.U[ax] - b.U[ax]);
    }

    let sizeL = M;
    let sizeR = M;
    if (E.length % M !== 0) {
        const sizeLR = (E.length % M) + M;
        sizeL = Math.floor(sizeLR / 2);
        sizeR = sizeLR - sizeL;
    }

    const nodes = [];
    nodes.push(Node.createByEntries(E.splice(0, sizeL)));
    nodes.push(Node.createByEntries(E.splice(-sizeR)));

    const split = Math.floor(E.length / M / 2) * M;
    const right = E.splice(split);
    nodes.push(...pseudoPRSplit(E, m, M, dim, (dir + 1) % dim));
    nodes.push(...pseudoPRSplit(right, m, M, dim, (dir + 1) % dim));
    return nodes;
}