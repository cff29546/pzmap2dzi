// reference: 
//     "R-Trees: A Dynamic Index Structure for Spatial Searching" (SIGMOD 1984)
//     https://doi.org/10.1145/971697.602266
//
//     "The R*-tree: an efficient and robust access method for points and rectangles" (SIGMOD 1990)
//     https://doi.org/10.1145/93597.98741
//
//     "The priority R-tree: A practically efficient and worst-case optimal R-tree" (SIGMOD 2004)
//     https://doi.org/10.1145/1328911.1328920
//
//     ELKI R*-tree implementation:
//     https://github.com/elki-project/elki

import * as Node from './node.js';
import * as Strategy from './strategy.js';

// item definition
// {
//   I: <item data>,
//   U: [<upper bound dimension 0>, <upper bound dimension 1>, ...],
//   L: [<lower bound dimension 0>, <lower bound dimension 1>,
// }
// node definition
// {
//   E: [<entry 0>, <entry 1>, ...],
//   U: [<upper bound dimension 0>, <upper bound dimension 1>, ...],
//   L: [<lower bound dimension 0>, <lower bound dimension 1>,
// }

export class RTree {
    constructor(options) {
        const {
            maxEntries = 9,
            minEntries = 4,
            dimensions = 2,
            strategy = null,
        } = options || {};
        this.M = maxEntries;
        this.m = minEntries;
        if (this.M < 2 || this.m > this.M / 2) {
            throw new Error(`Invalid R-tree parameters m=${this.m} M=${this.M}: M must be >= 2 and m must be <= M/2`);
        }
        this.dim = dimensions;
        this.height = 0;
        this.root = null;
        const {
            chooseSubTree = 'MIN_OVERLAP',
            split = 'MIN_OVERLAP',
            batchLoad = 'PR_TREE',
            condense = true,
        } = strategy || {};
        this.chooseSubTree = Strategy.CHOOSE_SUB_TREE[chooseSubTree];
        if (!this.chooseSubTree) {
            this.chooseSubTree = Strategy.CHOOSE_SUB_TREE.MIN_AREA_EXPAND;
        }
        this.split = Strategy.SPLIT[split];
        if (!this.split) {
            this.split = Strategy.SPLIT.MIN_OVERLAP;
        }
        this.batchLoad = Strategy.BATCH_LOAD[batchLoad];
        this.condense = condense;
    }

    clear() {
        this.root = null;
        this.height = 0;
    }

    load(root) {
        this.clear();
        this.insert(root);
    }

    _findInsertionPath(node, height) {
        const path = [];
        let current = this.root;
        let currentHeight = this.height;
        while (currentHeight > height) {
            path.push(current);
            current = this.chooseSubTree(current, node);
            if (!current) {
                throw new Error('chooseSubTree returned null');
            }
            currentHeight--;
        }
        return path;
    }

    // Insert a node
    // Node can be a data item (height === 0) or a root node for another R-tree (height > 0).
    // If height is not given, it will be calculated by traversing the node.
    insert(node, height = null) {
        if (height === null) {
            height = Node.getHeight(node);
        }
        if (height < 0) {
            return false;
        }
        if (!this.root) {
            if (height === 0) {
                this.root = Node.createByEntries([node]);
                this.height = 1;
            } else {
                this.root = node;
                this.height = height;
            }
            return true;
        }

        if (height > this.height) {
            // swap root and node when node is deeper
            [this.root, node] = [node, this.root];
            [this.height, height] = [height, this.height];
        }

        const path = this._findInsertionPath(node, height);
        let current = null;
        if (path.length === 0) {
            // node is at the same height as root, this guarantees that the node is not an item
            // try to merge root, as root is allowed to have less than m entries
            this.root.E.push(...node.E);
            current = this.root;
        } else {
            // insert the node into the located parent
            current = path.pop();
            current.E.push(node);
        }
        while (current.E.length > this.M) {
            const splitNode = this.split(current, this.m);
            if (path.length === 0) {
                // leaf === root, split root
                this.root = Node.createByEntries([current, splitNode]);
                this.height++;
                return true;
            } else {
                // insert split node into parent
                current = path.pop();
                current.E.push(splitNode);
            }
        }
        if (current) {
            // adjust leaf
            Node.adjustByEntries(current);
        }
        while (path.length > 0) {
            current = path.pop();
            Node.adjustByEntries(current);
        }
        return true;
    }

    batchInsert(items) {
        if (this.batchLoad) {
            const root = this.batchLoad(items, this.m, this.M, this.dim);
            this.insert(root);
        } else {
            for (const item of items) {
                this.insert(item);
            }
        }
    }

    _findItemPath(item) {
        if (!this.root) {
            return [];
        }

        // DFS to find the item
        const path = [];
        if (Node.contains(this.root, item)) {
            path.push([this.root, -1]); // start with root and index 0
        }
        while (path.length > 0) {
            const [current, index] = path.pop();
            if (Node.isItem(current)) {
                if (current.I === item.I) {
                    return path; // return first match
                }
                continue;
            }

            // continue with children
            for (let i = index + 1; i < current.E.length; i++) {
                const entry = current.E[i];
                if (Node.contains(entry, item)) {
                    // found a child that contains the item
                    path.push([current, i]); // push the child index
                    path.push([entry, -1]);  // push the child itself with index -1 to start from the beginning
                    break;
                }
            }
            // all children missed, done with current (no need to push it back)
        }
        return [];
    }

    delete(item) {
        const path = this._findItemPath(item);
        if (path.length === 0) {
            return false; // Item not found
        }

        let [current, index] = path.pop();
        current.E.splice(index, 1); // remove the item from the leaf
        if (this.condense) {
            // TODO: condense mode
            let height = 0;
            const orphaned = [];
            while (current.E.length < this.m && path.length > 0) {
                orphaned.push([current.E, height]);
                const [parent, parentIndex] = path.pop();
                parent.E.splice(parentIndex, 1);
                current = parent; // continue with the parent
                height++;
            }

            if (path.length === 0) {
                // leaf is root
                if (this.root.E.length === 0) {
                    // root is empty, clear the tree
                    this.clear();
                } else if (this.root.E.length === 1 && !Node.isItem(this.root.E[0])) {
                    // root has only one entry, promote it
                    this.root = this.root.E[0];
                    this.height--;
                } else {
                    Node.adjustByEntries(this.root); // adjust the root
                }
            } else {
                Node.adjustByEntries(current); // adjust the node
                while (path.length > 0) {
                    const [parent, _] = path.pop();
                    Node.adjustByEntries(parent); // adjust the parent
                }
            }

            // reinsert orphaned entries
            for (const [entries, h] of orphaned) {
                for (const entry of entries) {
                    this.insert(entry, h);
                }
            }
        } else {
            // no condense mode, only remove node with no entries
            while (current.E.length === 0 && path.length > 0) {
                const [parent, parentIndex] = path.pop();
                parent.E.splice(parentIndex, 1); // remove the empty node from the parent
                current = parent; // continue with the parent
            }
            if (current.E.length === 0) {
                // root is empty, clear the tree
                this.clear();
            } else {
                Node.adjustByEntries(current); // adjust the node
                while (path.length > 0) {
                    const [parent, _] = path.pop();
                    Node.adjustByEntries(parent); // adjust the parent
                }
            }
        }
    }
    
    items() {
        return Node.allItems(this.root);
    }

    query(box) {
        if (!this.root) {
            return [];
        }

        // TODO validate implementation
        // DFS to find all items that intersect with the box
        const result = [];
        const stack = [];
        if (Node.overlapArea(this.root, box) > 0) {
            stack.push([this.root, -1]); // start with root and index -1
        }

        while (stack.length > 0) {
            const [current, index] = stack.pop();
            if (index == -1) {
                if (Node.isItem(current)) {
                    if (Node.overlapArea(box, current) > 0) {
                        // item intersects with the box
                        result.push(current);
                    }
                    continue;
                }
                if (Node.contains(box, current)) {
                    // box contains the current node, add all items
                    Node.allItems(current, result);
                    continue;
                }
            }
            // continue with children
            for (let i = index + 1; i < current.E.length; i++) {
                const entry = current.E[i];
                if (Node.overlapArea(entry, box) > 0) {
                    // found a child that intersects with the box
                    stack.push([current, i]); // push the child index
                    stack.push([entry, -1]);  // push the child itself with index -1 to start from the beginning
                    break; // break to start with the next child
                }
            }
        }
        return result;
    }
}

export function validate(rtree) {
    if (rtree.root === null) {
        return [rtree.height === 0, -1];
    }
    return _validateNode(rtree, rtree.root, rtree.height);
}

function _validateNode(rtree, node, height) {
    if (!node) {
        return [false, -1];
    }
    if (Node.isItem(node)) {
        return [height === 0, 0];
    }

    let valid = true;
    let childHeight = new Set();
    if (node.E.length === 0 || node.E.length > rtree.M) {
        valid = false; // node has invalid number of entries
    }
    if (rtree.condense && node !== rtree.root && node.E.length < rtree.m) {
        valid = false; // node has invalid number of entries
    }
    for (const entry of node.E) {
        if (!Node.contains(node, entry)) {
            valid = false;
        }
        const [childValid, h] = _validateNode(rtree, entry, height - 1);
        valid = valid && childValid;
        childHeight.add(h);
    }
    if (childHeight.size > 1) {
        valid = false; // all children must have the same height
    }
    return [valid, Math.max(...childHeight) + 1];
}

export function totalOverlap(rtree) {
    if (!rtree.root) {
        return 0;
    }
    let total = 0;
    const stack = [rtree.root];
    while (stack.length > 0) {
        const current = stack.pop();
        if (!Node.isItem(current)) {
            for (let i = 0; i < current.E.length; i++) {
                const entry = current.E[i];
                for (let j = i + 1; j < current.E.length; j++) {
                    total += Node.overlapArea(entry, current.E[j]);
                }
                stack.push(entry);
            }
        }
    }
    return total;
}