export function changeStyle(selector, cssProp, cssVal) {
    const rules = (document.all) ? 'rules' : 'cssRules';
    for (let i=0, len=document.styleSheets[0][rules].length; i<len; i++) {
        if (document.styleSheets[0][rules][i].selectorText === selector) {
            document.styleSheets[0][rules][i].style[cssProp] = cssVal;
        }
    }
}

export function setOutput(id, color, text, timeout=0) {
    const output = document.getElementById(id);
    if (output) {
        if (color !== null) {
            output.style.color = color;
        }
        output.innerHTML = text;
        if (timeout > 0) {
           setTimeout(setOutput, timeout, id, color, '', 0); 
        }
    }
}

function randomU32() {
    return Number.parseInt(Math.random().toString(16).substring(2).padEnd(8, '0').substring(0, 8), 16)
}

var lastTs = '';
var lastSeq = 0;
export function uniqueId() {
    const ts = Date.now().toString(36);
    const seq = ((ts === lastTs) ? lastSeq + 1 : randomU32());
    lastTs = ts;
    lastSeq = seq;
    return ts + '_' + seq.toString(36);
}

export function setValue(id, v) {
    const e = document.getElementById(id);
    if (e) {
        e.value = v;
    }
}

export function setChecked(id, v) {
    const e = document.getElementById(id);
    if (e) {
        e.checked = v;
    }
}

export function getValue(id) {
    const e = document.getElementById(id);
    if (e) {
        return e.value;
    }
    return null;
}

export function getChecked(id) {
    const e = document.getElementById(id);
    if (e) {
        return e.checked;
    }
    return null;
}

export function download(filename, data) {
    const e = document.createElement('a');
    e.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(data));
    e.setAttribute('download', filename);
    e.style.display = 'none';
    document.body.appendChild(e);
    e.click();
    document.body.removeChild(e);
}

export function upload() {
    const e = document.createElement('input');
    e.type = 'file';
    e.style.display = 'none';
    document.body.appendChild(e);
    return new Promise(function(resolve, reject) {
        const callback = (event) => {resolve(event); document.body.removeChild(e);};
        e.addEventListener('cancel', callback);
        e.addEventListener('change', callback);
        e.click();
    }).then((event) => {
        if (event.type == 'change') {
            const file = event.target.files[0];
            return new Promise(function(resolve, reject) {
                const reader = new FileReader();
                reader.onload = (e) => { resolve(e.target.result); };
                reader.readAsText(file);
            });
        } else {
            return Promise.resolve(null);
        }
    });
}

export function parseJson(data) {
    try {
        return JSON.parse(data);
    } catch (error) {
        return null;
    }
}

export function format(template, args) {
    let formatted = template;
    for(const arg in args) {
        formatted = formatted.replace("{" + arg + "}", args[arg]);
    }
    return formatted;
};

export function isObject(o) {
    return (typeof o === 'object' && !Array.isArray(o) && o !== null);
}

export function objectEqual(a, b) {
    if (a === b) return true;
    if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    for (const key of keysA) {
        if (!keysB.includes(key) || !objectEqual(a[key], b[key])) return false;
    }
    return true;
}

export function getByPath(o, ...args) {
    for (const key of args) {
        if (o === undefined || o === null) {
            return o;
        }
        o = o[key];
    }
    return o;
}

export function setClipboard(text) {
    return navigator.clipboard.writeText(text)
        .then(() => Promise.resolve(null))
        .catch((err) => Promise.resolve(err));
}

export function getColorValue(name) {
    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    context.fillStyle = name;
    context.fillRect(0,0,1,1);
    return context.getImageData(0,0,1,1).data;
}

var isLightColorCache = {};
export function isLightColor(name) {
    if (isLightColorCache[name] !== undefined) {
        return isLightColorCache[name];
    }
    const [r, g, b, a] = getColorValue(name);
    // https://en.wikipedia.org/wiki/Rec._709#Luma_coefficients
    const luma = (r * 2126 + g * 7152 + b * 722) / 10000;
    isLightColorCache[name] = (luma > 128);
    return isLightColorCache[name];
}