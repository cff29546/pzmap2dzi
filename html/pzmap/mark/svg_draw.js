import { g } from "../globals.js";
import { rectsToPolygons } from "../algorithm/geometry/rects_intersection.js";
import * as util from "../util.js";

export function updateViewport(viewer, map) {
    const range = g.range;
    const viewBox = [];
    if (range.diffSum) {
        viewBox.push((range.minDiff + 1)/2, range.minSum/4, (range.maxDiff - range.minDiff - 2)/2, (range.maxSum - range.minSum - 2)/4);
    } else {
        viewBox.push(range.minX, range.minY, range.maxX - range.minX - 1, range.maxY - range.minY - 1);
    }
    g.svg.svg.setAttribute('viewBox', viewBox.join(' '));
}

export function updateZoom() {
    const step = g.grid.step;
    g.svg.iso.setAttribute('stroke-width', 2 * g.zoomInfo.rectBorder / step);
    g.svg.iso_active.setAttribute('stroke-width', 2 * g.zoomInfo.rectBorder / step);
    const fontSize = 16 * ({
        small: 1.5,
        medium: 1.75,
        large: 2,
    }[g.zoomInfo.fontSize] || 1.75);
    g.svg.top.setAttribute('stroke-width', g.zoomInfo.rectBorder / step);
    g.svg.top_active.setAttribute('stroke-width', g.zoomInfo.rectBorder / step);
    g.svg.text.setAttribute('stroke-width', g.zoomInfo.rectBorder / step);
    //g.svg.text.setAttribute('transform', 'translate(0,' + ((g.zoomInfo.pointSize / 2 + 5) / step) + ')');

    util.changeStyle('svg use.iso.cursor', 'stroke-width', g.zoomInfo.rectBorder / step);
    util.changeStyle('svg use.top.cursor', 'stroke-width', g.zoomInfo.rectBorder / step / 2);
    for (let i = 0; i < 3; i++) {
        util.changeStyle('svg text.line' + i, 'transform',
            'matrix(1,0,0,1,0,' + ((g.zoomInfo.pointSize / 2 + 8 + i * (5 + fontSize)) / step) + ')');
    }
    util.changeStyle('svg text', 'font-size', (fontSize / step) + 'px');
    util.changeStyle('svg text', 'stroke-width', 4 / step);
    util.changeStyle('svg circle', 'r', g.zoomInfo.pointSize / 2 / step);
    util.changeStyle('svg circle', 'stroke-width', 2 / step);
}

class EventAdapter {
    static _instance = null;
    constructor() {
        if (EventAdapter._instance) {
            return EventAdapter._instance
        }
        EventAdapter._instance = this;
        this.listener = null; // edit
    }

    setListener(listener) {
        this.listener = listener;
    }

    getCoords(event) {
        const rect = g.svg.svg.getBoundingClientRect();
        const mx = event.pointerX - rect.left;
        const my = event.pointerY - rect.top;
        const range = g.range;
        if (range.diffSum) {
            const diff = range.minDiff + mx * (range.maxDiff - range.minDiff) / rect.width;
            const sum = range.minSum + my * (range.maxSum - range.minSum - 2) / rect.height;
            const x = (sum + diff) / 2;
            const y = (sum - diff) / 2;
            return { x, y };
        } else {
            const x = range.minX + mx * (range.maxX - range.minX - 1) / rect.width;
            const y = range.minY + my * (range.maxY - range.minY - 1) / rect.height;
            return { x, y };
        }
    }

    onEvent(eventName, event) {
        let handled = false;
        if ((eventName === 'pointerdown' && event.buttons & 1)) {
            if (this.listener && this.listener.pointerdown) {
                if (this.listener.pointerdown(event)) {
                    handled = true;
                }
            }
        }
        if (!handled) {
            g.svg.iso_active.style.pointerEvents = 'none';
            g.svg.top_active.style.pointerEvents = 'none';
            const eventType = event.constructor;
            const target = document.elementFromPoint(event.clientX, event.clientY);
            g.svg.iso_active.style.pointerEvents = 'auto';
            g.svg.top_active.style.pointerEvents = 'auto';
            target.dispatchEvent(new eventType(eventName, event));
        }
    }
}

export function init() {
    if (!g.svg) {
        g.svg = {
            svg: document.getElementById('svg_overlay'),
            iso: document.getElementById('svg_iso'),
            iso_active: document.getElementById('svg_iso_active'),
            top: document.getElementById('svg_top'),
            top_active: document.getElementById('svg_top_active'),
            text: document.getElementById('svg_text'),
            defs: document.getElementById('svg_defs'),
            adapter: new EventAdapter(),
        };
        for (const eventName of ['click', 'pointerdown', 'pointermove', 'pointerup', 'wheel']) {
            g.svg.iso_active.addEventListener(eventName, g.svg.adapter.onEvent.bind(g.svg.adapter, eventName));
            g.svg.top_active.addEventListener(eventName, g.svg.adapter.onEvent.bind(g.svg.adapter, eventName));
        }
    }
    g.svg.iso.innerHTML = '';
    g.svg.iso_active.innerHTML = '';
    g.svg.top.innerHTML = '';
    g.svg.top_active.innerHTML = '';
    g.svg.text.innerHTML = '';
    g.svg.defs.innerHTML = '';
}

function getClasses(mark, part, extra=null) {
    const classes = [];
    classes.push(g.map_type);
    if (mark.cls) {
        classes.push(...mark.cls);
    }
    if (part.cls) {
        classes.push(...part.cls);
    }
    if (extra) {
        classes.push(...extra);
    }
    return classes.join(' ');
}

function appendShape(shape, interactive, type=null) {
    const target = (type || g.map_type) + (interactive ? '_active' : '');
    g.svg[target].appendChild(shape);
}

function newSVGElement(type, id=null, attrs={}) {
    const elem = document.createElementNS("http://www.w3.org/2000/svg", type);
    if (id) {
        elem.setAttribute("id", id);
    }
    for (const [key, value] of Object.entries(attrs)) {
        elem.setAttribute(key, value);
    }
    return elem;
}

function newPath(id, points, close=true) {
    const d = ['M'];
    for (const { x, y } of points) {
        d.push(x, y, 'L');
    }
    d.pop();
    if (close) d.push('Z');
    const path = newSVGElement('path', id, { d: d.join(' ') });
    return path;
}

function newClip(id, pathId) {
    const clip = newSVGElement('clipPath', id);
    clip.appendChild(newSVGElement('use', null, { href: '#' + pathId }));
    return clip;
}

function newMask(id, pathId, masksIds) {
    const mask = newSVGElement('mask', id);
    mask.appendChild(newSVGElement('use', null, { href: '#' + pathId, fill: 'white' }));
    for (const maskId of masksIds) {
        mask.appendChild(newSVGElement('use', null, { href: '#' + maskId, fill: 'black' }));
    }
    return mask;
}

function newPolygon(id, points, masks, color, background, cls=null) {
    const defs = g.svg.defs.appendChild(newSVGElement('g', id));
    defs.appendChild(newPath(id + '-p', points));
    const maskIds = [];
    if (masks && masks.length > 0) {
        for (let i = 0; i < masks.length; i++) {
            const maskId = id + '-p-' + i;
            defs.appendChild(newPath(maskId, masks[i]));
            maskIds.push(maskId);
        }
        defs.appendChild(newMask(id + '-m', id + '-p', maskIds));
    } else {
        defs.appendChild(newClip(id + '-c', id + '-p'));
    }
    const attrs = {
        href: '#' + id + '-p',
        stroke: color,
        fill: background,
    };
    if (maskIds.length > 0) {
        attrs['mask'] = 'url(#' + id + '-m)';
    } else {
        attrs['clip-path'] = 'url(#' + id + '-c)';
    }
    const group = newSVGElement('g', id + '-u');
    const use = newSVGElement('use', id + '-u-0', attrs);
    if (cls) use.setAttribute('class', cls);
    group.appendChild(use);
    for (let i = 0; i < maskIds.length; i++) {
        const maskId = maskIds[i];
        const mask = newSVGElement('use', id + '-m-' + i, {
            href: '#' + maskId,
            stroke: color,
            mask: 'url(#' + id + '-m)'
        });
        if (cls) mask.setAttribute('class', cls);
        group.appendChild(mask);
    }
    return group;
}

function text(id, mark, part) {
    let { x, y } = part;
    x += 0.5;
    y += 0.5;
    const layer = mark.layer || 0;
    let fill =  part.color || mark.color;
    if (!fill) {
        fill = defaultColor(mark)[1];
    }
    if (mark.selected) {
        fill = '#ff3';
    }
    const stroke = util.isLightColor(fill) ? 'black' : 'white';
    const attrs = { x, y, stroke, fill };
    let [dx, dy] = part.rotate || [0, 0];
    if (g.map_type === 'iso') {
        if (part.rotate) {
            [dx, dy] = [(dx - dy) / 2, (dx + dy) / 4];
        }
        attrs.x = (x - y) / 2;
        attrs.y = (x + y - layer * 6) / 4;
    }
    const texts = part.text.split('\n');
    let container = g.svg.text;
    if (texts.length > 1) {
        container = newSVGElement('g', id + '-u');
        g.svg.text.appendChild(container);
    }
    for (let i = 0; i < texts.length; i++) {
        const textLine = texts[i];
        const lineId = i ? (id + '-u-' + i) : id;
        const e = newSVGElement('text', lineId, attrs);
        e.innerHTML = textLine;
        const classes = ['line' + i];
        if (mark.font) e.setAttribute('font-family', mark.font);
        if (part.rotate) {
            let rotate = 0;
            if (dx === 0) {
                rotate = 90;
            } else {
                rotate = Math.atan2(dy, dx) * 180 / Math.PI;
                if (rotate < -90) rotate += 180;
                if (rotate > 90) rotate -= 180;
            }
            const rotateParam = [rotate, attrs.x, attrs.y];
            e.setAttribute('transform', 'rotate(' + rotateParam.join(',') + ')');
            classes.pop();
        }
        const cls = getClasses(mark, part, classes);
        e.setAttribute('class', cls);
        container.appendChild(e);
    }
}

function defaultColor(mark) {
    let c0 = '#39f';
    let c1 = '#33f';
    if (mark.layer < g.currentLayer) {
        c0 = '#99f';
        c1 = '#93f';
    }
    if (mark.layer > g.currentLayer) {
        c0 = '#9f3';
        c1 = '#383';
    }
    return [c0, c1];
}

function point(id, mark, part) {
    const { x, y } = part;
    let { color, background } = mark;
    const layer = mark.layer || 0;
    const attrs = { cx: x + 0.5, cy: y + 0.5 };
    if (g.map_type === 'iso') {
        attrs.cx = (x - y) / 2;
        attrs.cy = (x + y + 1 - layer * 6) / 4;
    }
    const e = newSVGElement('circle', id, attrs);
    if (!color && !background) {
        [background, color] = defaultColor(mark);
    }
    if (mark.selected) {
        background = '#ff3';
        color = '#881';
    }
    if (color) e.setAttribute('stroke', color);
    if (background) e.setAttribute('fill', background);
    const cls = getClasses(mark, part);
    e.setAttribute('class', cls);
    appendShape(e, mark.interactive, 'top');
}

function shiftPoints(points, layer) {
    const d = -layer * 3;
    return points.map(p => ({ x: p.x + d, y: p.y + d }));
}

function polygon(id, mark, part) {
    let color = mark.color;
    const background = mark.background || 'transparent';
    const layer = mark.layer || 0;
    let points = part.points;
    let masks = part.masks;
    if (g.map_type === 'iso' && layer !== 0) {
        points = shiftPoints(part.points, layer);
        if (masks && masks.length > 0) {
            masks = masks.map(mask => shiftPoints(mask, layer));
        }
    }
    if (!color) {
        color = defaultColor(mark)[0];
    }
    if (mark.selected) {
        color = '#ff3';
    }
    if (part.selected) {
        color = '#fff';
    }
    const cls = getClasses(mark, part);
    const polygon = newPolygon(id, points, masks, color, background, cls);
    appendShape(polygon, mark.interactive);
}

function polyline(id, mark, part) {
    let color = mark.color;
    const layer = mark.layer || 0;
    const { width, linecap, linejoin } = part;
    let points = part.points;
    if (g.map_type === 'iso' && layer !== 0) {
        points = shiftPoints(part.points, layer);
    }
    if (!color) {
        color = defaultColor(mark)[0];
    }
    if (mark.selected) {
        color = '#ff3';
    }
    const e = newPath(id, points, false);
    e.setAttribute('stroke', color);
    e.setAttribute('fill', 'none');
    if (width) e.setAttribute('stroke-width', width);
    if (linecap) e.setAttribute('stroke-linecap', linecap);
    if (linejoin) e.setAttribute('stroke-linejoin', linejoin);
    const cls = getClasses(mark, part);
    e.setAttribute('class', cls);
    appendShape(e, mark.interactive);
}

var _DRAW_FUNCTIONS = {
    point: point,
    text: text,
    polygon: polygon,
    polyline: polyline,
};

export function addPart(id, mark, part) {
    const func = _DRAW_FUNCTIONS[part.shape]
    if (func) {
       func(id, mark, part);
    }
}

export function addMark(id, mark) {
    if (mark.type === 'area') {
        const rects = mark.parts.filter(part => part.shape === 'rect');
        const polygons = rectsToPolygons(rects);
        if (mark.selected) {
            const selected = rects.filter(part => part.shape === 'rect' && part.selected);
            if (selected.length > 0) {
                const rect = rectsToPolygons(selected)[0];
                rect.selected = true;
                polygons.push(rect);
            }
        }
        mark.parts = mark.parts.filter(part => part.shape !== 'rect');
        for (let i = 0; i < polygons.length; i++) {
            const p = polygons[i];
            p.id = id + '-' + i;
            p.shape = 'polygon';
            if (mark.isDiffSum) {
                p.points = p.points.map(pt => ({ x: (pt.x + pt.y) / 2, y: (pt.y - pt.x) / 2 }));
                if (p.masks && p.masks.length > 0) {
                    p.masks = p.masks.map(mask => mask.map(pt => ({ x: (pt.x + pt.y) / 2, y: (pt.y - pt.x) / 2 })));
                }
            }
            mark.parts.push(p);
            //for (const [x, y] of part.points) point(util.uniqueId(), { color: 'red', background: 'white' }, { x, y });
        }
    }
    return true;
}

function remove(id) {
    const e = document.getElementById(id);
    if (e) {
        e.parentNode.removeChild(e);
        return true;
    }
    return false;
}

export function removePart(id) {
    let removed = 0;
    removed += remove(id + '-u');
    removed += remove(id);
    return removed > 0;
}

export function removeMark(id) {
    return true;
}