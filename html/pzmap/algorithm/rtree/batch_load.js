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

function pseudoPRSplit(E, m, M, dim, dir = 0, output = null) {
    // O(n log n) priority queue approach
    if (output === null) {
        output = [];
    }
    if (E.length === 0) {
        return output;
    }
    if (E.length <= M) {
        output.push(Node.createByEntries(E));
        return output;
    }

    const sizeLR = M + ((E.length % M) || M);
    const sizeL = sizeLR >> 1;
    const sizeR = sizeLR - sizeL;
    const split = Math.floor((E.length - sizeLR) / M / 2) * M;

    const ax = dir % dim;
    const d = (dir < dim) ? 'L' : 'U';
    const cmp = (a, b) => a[d][ax] - b[d][ax];
    const negcmp = (a, b) => b[d][ax] - a[d][ax];

    const pqL = new PriorityQueue(negcmp, sizeL);
    const pqR = new PriorityQueue(cmp, sizeR);
    const remaining = [];
    for (const e of E) {
        let removed = pqL.push(e);
        if (removed) {
            removed = pqR.push(removed);
        }
        if (removed) {
            remaining.push(removed);
        }
    }
    const pLeft = Node.createByEntries(pqL.items);
    const pRight = Node.createByEntries(pqR.items);
    partition(remaining, cmp, split);
    const right = remaining.splice(split);
    const left = remaining;


    output.push(pLeft, pRight);
    pseudoPRSplit(left, m, M, dim, (dir + 1) % (dim * 2), output);
    pseudoPRSplit(right, m, M, dim, (dir + 1) % (dim * 2), output);
    return output;
}

class PriorityQueue {
    constructor(cmp, maxSize) {
        this.cmp = cmp;
        this.items = [];
        this.maxSize = maxSize;
    }
    push(item) {
        if (this.items.length < this.maxSize) {
            this.items.push(item);
            this._siftUp();
            return null;
        } else {
            if (this.cmp(item, this.items[0]) > 0) {
                const top = this.items[0];
                this.items[0] = item;
                this._siftDown();
                return top;
            } else {
                return item;
            }
        }
    }
    _siftUp() {
        let idx = this.items.length - 1;
        const item = this.items[idx];
        while (idx > 0) {
            const parentIdx = (idx - 1) >> 1;
            const parent = this.items[parentIdx];
            if (this.cmp(item, parent) < 0) {
                this.items[idx] = parent;
                idx = parentIdx;
            } else {
                break;
            }
        }
        this.items[idx] = item;
    }
    _siftDown() {
        let idx = 0;
        const length = this.items.length;
        const item = this.items[idx];
        while (true) {
            const leftIdx = (idx << 1) + 1;
            const rightIdx = leftIdx + 1;
            let targetIdx = leftIdx;
            if (rightIdx < length && this.cmp(this.items[rightIdx], this.items[leftIdx]) < 0) {
                targetIdx = rightIdx;
            }
            if (targetIdx < length && this.cmp(this.items[targetIdx], item) < 0) {
                this.items[idx] = this.items[targetIdx];
                idx = targetIdx;
            } else {
                break;
            }
        }
        this.items[idx] = item;
    }
}

function partition(E, cmp, split, randomPivot = false) {
    // Dutch National Flag partitioning
    let start = 0;
    let end = E.length;

    while (start < end) {
        if (randomPivot) {
            const randIndex = Math.floor(Math.random() * (end - start)) + start;
            [E[start], E[randIndex]] = [E[randIndex], E[start]];
        }

        const pivot = E[start];
        let low = start;
        let mid = start + 1; // E[start] is pivot
        let high = end - 1;

        while (mid <= high) {
            const result = cmp(E[mid], pivot);
            if (result < 0) {
                [E[low], E[mid]] = [E[mid], E[low]];
                low++;
                mid++;
            } else if (result > 0) {
                [E[mid], E[high]] = [E[high], E[mid]];
                high--;
            } else {
                mid++;
            }
        }
        if (split < low) {
            end = low;
        } else if (split > mid) {
            start = mid;
        } else {
            return;
        }
    }
}

export var test = {};
if (typeof tests === 'function') { // for test
    test.PriorityQueue = PriorityQueue;
    test.partition = partition;
}