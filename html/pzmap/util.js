export function changeStyle(selector, cssProp, cssVal) {
    let rules = (document.all) ? 'rules' : 'cssRules';
    for (let i=0, len=document.styleSheets[0][rules].length; i<len; i++) {
        if (document.styleSheets[0][rules][i].selectorText === selector) {
            document.styleSheets[0][rules][i].style[cssProp] = cssVal;
        }
    }
}

export function setOutput(id, color, text, timeout=0) {
    let output = document.getElementById(id);
    if (output) {
        output.style.color = color;
        output.innerHTML = text;
        if (timeout > 0) {
           setTimeout(setOutput, timeout, id, color, '', 0); 
        }
    }
}

var lastTs = '';
var lastSeq = 0;

export function uniqueId() {
    let ts = Date.now().toString(36);
    let seq = Math.random().toString(36).substring(2);
    if (ts == lastTs) {
        seq = (Number.parseInt(lastSeq, 36) + 1).toString(36); 
    }
    lastTs = ts;
    lastSeq = seq;
    return ts + '_' + seq;
}

export function setValue(id, v) {
    let e = document.getElementById(id);
    if (e) {
        e.value = v;
    }
}

export function setChecked(id, v) {
    let e = document.getElementById(id);
    if (e) {
        e.checked = v;
    }
}

export function getValue(id) {
    let e = document.getElementById(id);
    if (e) {
        return e.value;
    }
    return null;
}

export function getChecked(id) {
    let e = document.getElementById(id);
    if (e) {
        return e.checked;
    }
    return null;
}

export function download(filename, data) {
    let e= document.createElement('a');
    e.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(data));
    e.setAttribute('download', filename);
    e.style.display = 'none';
    document.body.appendChild(e);
    e.click();
    document.body.removeChild(e);
}

export function upload() {
    let e = document.createElement('input');
    e.type = 'file';
    e.style.display = 'none';
    document.body.appendChild(e);
    return new Promise(function(resolve, reject) {
        let callback = (event) => {resolve(event); document.body.removeChild(e);};
        e.addEventListener('cancel', callback);
        e.addEventListener('change', callback);
        e.click();
    }).then((event) => {
        if (event.type == 'change') {
            let file = event.target.files[0];
            return new Promise(function(resolve, reject) {
                let reader = new FileReader();
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
    for( var arg in args ) {
        formatted = formatted.replace("{" + arg + "}", args[arg]);
    }
    return formatted;
};

export function isObject(o) {
    return (typeof o === 'object' && !Array.isArray(o) && o !== null);
}
