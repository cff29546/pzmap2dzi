import * as Node from './node.js';

// ChooseSubTree(node, item) -> node
// This function selects the subtree that is most suitable for inserting a new item.

// Min Area Expand (R-tree 1984)
export function minAreaExpand(node, item) {
    let bestChild = null;
    let bestExpandedArea = Infinity;
    let bestArea = Infinity;

    for (const child of node.E) {
        const expanded = Node.union(child, item);
        const area = Node.area(child);
        const areaExpanded = Node.area(expanded) - area;

        if (areaExpanded < bestExpandedArea || (areaExpanded === bestExpandedArea && area < bestArea)) {
            bestChild = child;
            bestArea = area;
            bestExpandedArea = areaExpanded;
        }
    }

    return bestChild;
}

// Min Overlap O(n^2) (R*-tree 1990)
export function minOverlap(node, item) {
    let bestChild = null;
    let bestOverlap = Infinity;
    let bestAreaExpanded = Infinity;
    let bestArea = Infinity;

    for (const child of node.E) {
        let overlap = 0;
        const area = Node.area(child);
        const areaExpanded = Node.area(Node.union(child, item)) - area;
        for (const other of node.E) {
            if (child !== other) {
                overlap += Node.overlapArea(child, other);
            }
        }

        if (overlap < bestOverlap
            || (overlap === bestOverlap && areaExpanded < bestAreaExpanded)
            || (overlap === bestOverlap && areaExpanded === bestAreaExpanded && area < bestArea)
        ) {
            bestChild = child;
            bestOverlap = overlap;
            bestAreaExpanded = areaExpanded;
            bestArea = area;
        }
    }

    return bestChild;
}
