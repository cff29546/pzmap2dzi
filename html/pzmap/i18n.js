import { g } from "./globals.js";
import * as util from "./util.js";

export const ALL = ['en', 'cn'];
const DEFAULT = ALL[0];
var lang = ALL[0];

var TEMPLATE = {};
var MAPPING = {};

export function setLang(l) {
    if (ALL.includes(l)) {
        lang = l;
        return true;
    }
    return false;
}

export function getLang() {
    return lang;
}

function getTemplate() {
    let data = TEMPLATE[lang];
    if (!data) {
        data = TEMPLATE[DEFAULT];
    }
    return data;
}

// get raw key value
function raw(key) {
    let t = getTemplate();
    if (t && t[key] != undefined) {
        return t[key];
    }
    return null;
}

// get raw key value
function getMapping() {
    let m = MAPPING;
    for (let key of arguments) {
        if (m && m[key] != undefined) {
            m = m[key];
        } else {
            return null;
        }
    }
    return m;
}

// substitute template
export function T(key, args=null) {
    let t = raw(key);
    if (t || t === '') {
        return util.format(t, args);
    } else {
        console.log('missing template [' + key + '] for [' + lang + ']')
        return key;
    }
}

// eval template, eval(`\`${e}\``)
export function E(key, args=null) {
    let e = raw(key);
    if (e || e === '') {
        return eval(`\`${e}\``);
    } else {
        console.log('missing eval template [' + key + '] for [' + lang + ']')
        return key;
    }
}

function resolve(v, args) {
    if (typeof v === 'string') {
        return T(v, args);
    }
    if (v.eval) {
        return E(v.eval, args);
    }
    return null;
}

// get labled text
function L(label, value, args) {
    let m = getMapping(label, value);
    let o = {};
    if (!util.isObject(m)) {
        return o;
    }
    for (let [k, v] of Object.entries(m)) {
        let val = resolve(v, args);
        if (val || val === '') {
            o[k] = val;
        } else {
            o[k] = 'missing template [' + v + '] lang=' + lang;
        }
    }
    return o;
}

// update all label
export function update(label, values=null, args=null) {
    let vset = null;
    if (values) {
        vset = new Set(values);
    }
    let labels = document.querySelectorAll('[' + label + ']');
    for (let l of labels) {
        if (vset === null || vset.has(l[label])) {
            let data = L(label, l[label], args);
            for (let [k, text] of Object.entries(data)) {
                l[k] = text;
            }
        }
    }
}

export function init() {
    let plist = [];
    let p = 0;
    for (let l of ALL) {
        let name = l;
        p = window.fetch('./pzmap/i18n/' + name + '.json');
        p = p.then((r)=>r.json()).catch((e)=>Promise.resolve(null));
        p = p.then((data)=>{TEMPLATE[name] = data; return Promise.resolve(name);});
        plist.push(p);
    }
    p = window.fetch('./pzmap/i18n/mapping.json');
    p = p.then((r)=>r.json()).catch((e)=>Promise.resolve({}));
    p = p.then((data)=>{MAPPING = data; return Promise.resolve(data);});
    plist.push(p);
    return Promise.all(plist);
}

// examples:
// T(key, args)
// E(key, args)
// resetLabels('id', ['a', 'b'])
