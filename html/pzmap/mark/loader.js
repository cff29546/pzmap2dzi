import { MarkManager } from "../marker.js";

onmessage = (e) => {
    const [r, options] = e.data;
    const indexes = [];
    for (let i = 0; i < r.length; i++) {
        if (!r[i] || !Array.isArray(r[i])) {
            r[i] = null;
            indexes.push(null);
            continue;
        }
        const mark = new MarkManager(options[i]);
        mark.disable();
        mark.load(r[i]); // add id if missing
        const index = mark.db.dumpIndex();
        indexes.push(index);
    }
    postMessage([r, indexes]);
};