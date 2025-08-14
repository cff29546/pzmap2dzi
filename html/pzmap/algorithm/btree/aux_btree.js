// btree.js
// reference: https://www.cs.princeton.edu/~dpw/courses/cos326-12/ass/2-3-trees.pdf
class Node {
    constructor(slots = null) {
        // slots: [child1, value1, child2, value2, child3, ...]
        this.slots = slots;
    }
}

export class BTree {
    constructor(order = 9, cmp = null, key = null, auxUp = null) {
        // cmp: function to compare two values, if omitted, uses default numeric comparison
        // key: function to extract key from a value, if omitted, uses the value itself
        // order: the maximum number of children in a node
        // order = 3 means a 2-3 tree
        // order = 4 means a 2-3-4 tree
        // auxUp: function for updating auxiliary data on each node (bottom-up aggregation)
        if (order < 3) {
            throw new Error(`Invalid order value ${order} for B-tree, must be >= 3`);
        }
        this.root = null;
        this.order = order;
        this.maxSlots = order * 2 - 1;
        this.minSlots = Math.ceil(order / 2) * 2 - 1;
        if (auxUp instanceof Function) {
            this.auxUp = auxUp;
        } else {
            this.auxUp = null;
        }
        if (cmp === null) {
            cmp = (a, b) => a - b; // default numeric comparison
        }
        if (key !== null) {
            this.cmp = (a, b) => cmp(key(a), key(b));
        } else {
            this.cmp = cmp; // use the provided comparison function directly
        }
    }

    _update(node) {
        if (this.auxUp !== null) {
            return this.auxUp(node);
        }
        return false; // skip propagating auxiliary data if no update function is provided
    }

    _locate(value, stopOnFound = false) {
        const path = [];
        let targetNode = null;
        let targetIndex = -1;
        let currentNode = this.root;
        while (currentNode !== null) {
            let index = 1;
            for (; index < currentNode.slots.length; index += 2) {
                if (this.cmp(value, currentNode.slots[index]) < 0) {
                    break;
                }
                if (this.cmp(currentNode.slots[index], value) === 0) {
                    targetNode = currentNode;
                    targetIndex = index;
                    if (stopOnFound) {
                        return [targetNode, targetIndex, path];
                    }
                    break; // design choice: goes to the left child
                }
            }
            index -= 1;
            path.push([currentNode, index]);
            currentNode = currentNode.slots[index];
        }
        return [targetNode, targetIndex, path];
    }

    insert(value) {
        let newNode = new Node([null, value, null]);
        const [targetNode, targetIndex, path] = this._locate(value);
        let needUpdate = true;
        while ((newNode !== null || needUpdate) && path.length > 0) {
            const [node, index] = path.pop();
            if (newNode !== null) {
                newNode = this._insert(node, index, newNode);
            }
            if (newNode === null) {
                // If newNode is null, it means the insertion was absorbed into the tree
                // the auxiliary data might still need to propagate up
                needUpdate = this._update(node);
            }
        }
        if (newNode !== null) {
            // If we still have a newNode, level up the tree
            this.root = newNode;
            this._update(this.root);
        }
    }

    _split(slots, right) {
        // Split slots into two parts, the left part reuses slots
        // mid = 1 + ((slots.length >> 2) << 1); // middle value index
        // mid + 1 // right part
        right.slots = slots.splice((1 + (slots.length >> 2)) << 1);
        return slots.pop(); // middle value
    }

    _insert(node, index, newNode) {
        // newNode contains only one value and two children which height equals to the children of node
        node.slots.splice(index, 1, ...newNode.slots);
        if (node.slots.length > this.maxSlots) {
            const value = this._split(node.slots, newNode); // Split the node, reuse newNode as right part
            this._update(node);
            this._update(newNode);
            return new Node([node, value, newNode]);
        }
        return null; // No new node created, insertion absorbed
    }

    search(value) {
        const [targetNode, targetIndex, path] = this._locate(value, true);
        if (targetNode === null) {
            return null; // Value not found
        }
        return targetNode.slots[targetIndex]; // Return the found value
    }

    delete(value) {
        const [targetNode, targetIndex, path] = this._locate(value);
        if (targetNode === null) {
            return null; // Value not found
        }
        const valueFound = targetNode.slots[targetIndex];

        let [holeNode, index] = path.pop();
        index += 1; // Point to the value
        if (index >= holeNode.slots.length) {
            index -= 2;
        }

        // Remove the value and ensure the hole is on a leaf node
        targetNode.slots[targetIndex] = holeNode.slots[index];
        let targetUpdated = targetNode === holeNode;
        holeNode.slots.splice(index, 2);
        if (holeNode.slots.length >= this.minSlots) {
            this._update(holeNode);
            holeNode = null; // No need to fix the hole, it has enough slots
        }

        let needUpdate = true;
        while ((holeNode !== null || needUpdate || !targetUpdated) && path.length > 0) {
            const [node, index] = path.pop();
            if (targetNode === node) {
                targetUpdated = true;
                needUpdate = true;
            }
            if (holeNode !== null) {
                holeNode = this._delete(node, index);
            }
            if (holeNode === null) {
                // If holeNode is null, it means the deletion was absorbed into the tree
                // the auxiliary data might still need to propagate up
                if (needUpdate) {
                    needUpdate = this._update(node);
                }
            }
        }
        if (holeNode !== null) {
            if (holeNode.slots.length === 1) {
                // Remove holeNode when only one slot left (root can break minSlots rule)
                this.root = holeNode.slots[0];
            } else {
                // root node can legally have slots between 2 and minSlots-1; still need to update auxiliary data
                this._update(holeNode);
            }
        }
        return valueFound;
    }

    _delete(node, index) {
        // Borrow from the left sibling, unless it's the first child
        index = index === 0 ? 0 : index - 2;
        const [left, value, right] = node.slots.splice(index, 3);
        left.slots.push(value, ...right.slots); // Merge siblings and the value
        
        if (left.slots.length > this.maxSlots) {
            // Split the left node
            const midValue = this._split(left.slots, right);
            node.slots.splice(index, 0, left, midValue, right);
            this._update(left);
            this._update(right);
            return null; // The holeNode was absorbed into the tree
        } else {
            // No split needed for left node, drop the right node
            node.slots.splice(index, 0, left);
            this._update(left);
            if (node.slots.length < this.minSlots) {
                return node; // Return the holeNode if it has too few slots
            } else {
                return null; // The holeNode was absorbed into the tree
            }
        }
    }

    inorderTraversal(node = this.root, result = null) {
        result = result || [];
        if (node === null) return result;
        for (let i = 0; i < node.slots.length; i += 1) {
            if (i & 1) {
                result.push(node.slots[i]);
            } else {
                this.inorderTraversal(node.slots[i], result);
            }
        }
        return result;
    }
}

// Function to validate a B-tree
// (BTree) -> [isValid: boolean, height: number]
export function validate(btree, validateData = null) {
    return _validateNode(btree, btree.root, validateData, null, null);
}

function _validateNode(btree, node, validateData, valueMin, valueMax) {
    if (node === null) return [true, 0]; // Empty node is valid with height 0

    const height = new Set();
    let valid = node === btree.root || (node.slots.length >= btree.minSlots && node.slots.length <= btree.maxSlots);
    let last = valueMin;

    for (let i = 1; i < node.slots.length + 2; i += 2) {
        const value = i < node.slots.length ? node.slots[i] : valueMax;
        if (value !== null && last !== null && btree.cmp(value, last) < 0) valid = false;
        if (value !== null && valueMax !== null && btree.cmp(valueMax, value) < 0) valid = false;
        const [childValid, childHeight] = _validateNode(btree, node.slots[i - 1], validateData, last, value);
        valid = valid && childValid;
        height.add(childHeight);
        last = value;
    }

    if (height.size > 1) {
        valid = false; // All children must have the same height
    }
    if (validateData && !validateData(node)) {
        valid = false;
        console.error('Validation failed for node:', node);
    }   
    return [valid, Math.max(...height) + 1];
}