export function cmpArray(a, b) {
    const len = a.length < b.length ? a.length : b.length;
    for (let i = 0; i < len; i++) {
        if (a[i] !== b[i]) {
            return a[i] - b[i];
        }
    }
    return a.length - b.length;
}