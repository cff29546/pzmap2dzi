import * as Node from './node.js';

// Split(node, m) -> node2
// This function splits a node into two nodes with at least m entries each.
// The first part reuses the input node, the second part is returned as a new node.
// both nodes should be adjusted to fit the R-tree properties.

// Min Overlap (R*-tree 1990)
// Slightly modified, considering candidates from all axis.
export function minOverlap(node, m) {
    let bestOverlap = Infinity;
    let bestPerimeter = Infinity;
    let bestArea = Infinity;
    let bestSplit = null;

    const orders = [];
    for (let d = 0; d < node.L.length; d++) {
        const orderL = node.E.toSorted((a, b) => a.L[d] === b.L[d] ? a.U[d] - b.U[d] : a.L[d] - b.L[d]);
        orders.push(orderL);
        const orderU = node.E.toSorted((a, b) => a.U[d] === b.U[d] ? a.L[d] - b.L[d] : a.U[d] - b.U[d]);
        orders.push(orderU);
    }
    for (const order of orders) {
        const result = splitOrderedEntriesMinOverlap(order, m);
        if (!result) continue;
        if (result.overlap < bestOverlap
            || (result.overlap === bestOverlap && result.perimeter < bestPerimeter)
            || (result.overlap === bestOverlap && result.perimeter === bestPerimeter && result.area < bestArea)) {
            bestSplit = result.split;
            bestOverlap = result.overlap;
            bestPerimeter = result.perimeter;
            bestArea = result.area;
        }
    }

    if (!bestSplit) {
        // Somehow failed to find a split
        // Fallback to splitting the node in half
        bestSplit = [
            node.E.slice(0, Math.ceil(node.E.length / 2)),
            node.E.slice(Math.ceil(node.E.length / 2))
        ];
    }
    node.E = bestSplit[0];
    Node.adjustByEntries(node);
    const node2 = Node.createByEntries(bestSplit[1]);
    return node2;
}

function splitOrderedEntriesMinOverlap(entries, m) {
    const n = entries.length;
    if (n < m * 2) return null; // Not enough entries to split
    const dim = entries[0].L.length;

    const left = Array(n-m*2+1);
    const right = Array(n-m*2+1);
    let leftBox = Node.infBox(dim);
    let rightBox = Node.infBox(dim);
    for (let i = 0; i < n - m; i++) {
        if (i < m) {
            Node.extend(leftBox, entries[i]);
            Node.extend(rightBox, entries[n - 1 - i]);
        } else {
            leftBox = Node.union(leftBox, entries[i]);
            rightBox = Node.union(rightBox, entries[n - 1 - i]);
        }

        if (i >= m - 1) {
            left[i + 1 - m] = leftBox;
            right[n - m - (i + 1)] = rightBox;
        }
    }
    let bestOverlap = Infinity;
    let bestPerimeter = Infinity;
    let bestArea = Infinity;
    let bestSplit = null;
    for (let i = 0; i < left.length; i++) {
        const overlap = Node.overlapArea(left[i], right[i]);
        const perimeter = Node.perimeter(left[i]) + Node.perimeter(right[i]);
        const area = Node.area(left[i]) + Node.area(right[i]);

        if (overlap < bestOverlap
            || (overlap === bestOverlap && perimeter < bestPerimeter)
            || (overlap === bestOverlap && perimeter === bestPerimeter && area < bestArea)) {
            bestOverlap = overlap;
            bestPerimeter = perimeter;
            bestArea = area;
            bestSplit = i;
        }
    }
    if (bestSplit === null) return null;
    return {
        split: [entries, entries.splice(bestSplit + m)],
        overlap: bestOverlap,
        perimeter: bestPerimeter,
        area: bestArea
    };
}