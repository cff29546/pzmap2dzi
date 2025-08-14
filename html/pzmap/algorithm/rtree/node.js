// bounding box / r-tree node definition
// {
//   U: [<upper bound dimension 0>, <upper bound dimension 1>, ...],
//   L: [<lower bound dimension 0>, <lower bound dimension 1>, ...],
//
//   E: [<child entry 0>, <child entry 1>, ...] // non-item nodes
//   I: <item data> // item nodes
// }
export function center(box) {
    let c = Array(box.L.length);
    for (let i = 0; i < box.L.length; i++) {
        c[i] = (box.L[i] + box.U[i]) / 2;
    }
    return c;
}

export function area(box) {
    let a = 1;
    for (let i = 0; i < box.L.length; i++) {
        a *= (box.U[i] - box.L[i]);
    }
    return a;
}

export function perimeter(box) {
    let p = 0;
    for (let i = 0; i < box.L.length; i++) {
        p += (box.U[i] - box.L[i]);
    }
    return p;
}

export function contains(box, other) {
    for (let i = 0; i < box.L.length; i++) {
        if (box.L[i] > other.L[i] || box.U[i] < other.U[i]) {
            return false;
        }
    }
    return true;
}

export function intersect(box, other) {
    for (let i = 0; i < box.L.length; i++) {
        if (box.U[i] < other.L[i] || box.L[i] > other.U[i]) {
            return false;
        }
    }
    return true;
}

export function overlapArea(box, other) {
    let area = 1;
    for (let i = 0; i < box.L.length; i++) {
        const l = (box.L[i] > other.L[i]) ? box.L[i] : other.L[i];
        const u = (box.U[i] < other.U[i]) ? box.U[i] : other.U[i];
        if (l >= u) {
            return 0; // no overlap
        }
        area *= (u - l);
    }
    return area;
}

export function extend(box, other) {
    for (let i = 0; i < box.L.length; i++) {
        if (box.L[i] > other.L[i]) {
            box.L[i] = other.L[i];
        }
        if (box.U[i] < other.U[i]) {
            box.U[i] = other.U[i];
        }
    }
}

export function infBox(dim) {
    return {
        L: Array(dim).fill(Infinity),
        U: Array(dim).fill(-Infinity)
    };
}
export function newBox(dim) {
    return { L: Array(dim), U: Array(dim) };
}

export function union(box, other) {
    const unionBox = newBox(box.L.length);
    for (let i = 0; i < box.L.length; i++) {
        unionBox.L[i] = box.L[i] < other.L[i] ? box.L[i] : other.L[i];
        unionBox.U[i] = box.U[i] > other.U[i] ? box.U[i] : other.U[i];
    }
    return unionBox;
}

export function isItem(box) {
    return !box.E;
}

export function allItems(node) {
    const items = [];
    const stack = [node];
    while (stack.length > 0) {
        const current = stack.pop();
        if (!current) continue;
        if (isItem(current)) {
            items.push(current);
        } else {
            stack.push(...current.E);
        }
    }
    return items;
}

export function adjustByEntries(box) {
    if (!box.E) {
        return;
    }
    const dim = box.E[0].L.length;
    box.L = Array(dim).fill(Infinity);
    box.U = Array(dim).fill(-Infinity);
    for (const e of box.E) {
        extend(box, e);
    }
}

export function createByEntries(entries, dim = null) {
    if (entries.length === 0) {
        if (dim === null) {
            return null;
        }
        const box = infBox(dim);
        box.E = [];
        return box;
    }
    const box = { E: entries };
    adjustByEntries(box);
    return box;
}

export function getHeight(node) {
    if (!node) {
        return -1;
    }
    let height = 0;
    while (node.E) {
        height++;
        if (node.E.length === 0) {
            return height;
        }
        node = node.E[0];
    }
    return height;
}