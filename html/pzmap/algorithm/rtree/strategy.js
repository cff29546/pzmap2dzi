import * as chooseSubTree from './choose_sub_tree.js';
import * as split from './split.js';
import * as batchLoad from './batch_load.js';

export const CHOOSE_SUB_TREE = {
    "MIN_AREA_EXPAND": chooseSubTree.minAreaExpand,
    "MIN_OVERLAP": chooseSubTree.minOverlap
}

export const SPLIT = {
    "MIN_OVERLAP": split.minOverlap
}

export const BATCH_LOAD = {
    "PR_TREE": batchLoad.prTree
}