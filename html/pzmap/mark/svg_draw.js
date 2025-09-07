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
    document.getElementById('svg_overlay').setAttribute('viewBox', viewBox.join(' '));
}

export function updateZoom() {
    const step = g.grid.step;
    g.svg.iso.setAttribute('stroke-width', 2 * g.zoomInfo.rectBorder / step);
    g.svg.top.setAttribute('stroke-width', g.zoomInfo.rectBorder / step);
    const fontSize = {
        small: 1.6,
        medium: 1.8,
        large: 2,
    }[g.zoomInfo.fontSize] || 1.8;
    //g.svg.top.setAttribute('font-size', (fontSize / g.zoomInfo.step) + 'em');
    util.changeStyle('svg text', 'font-size', (fontSize / step) + 'em');
    util.changeStyle('svg text', 'stroke-width', 4 / step);
    util.changeStyle('svg circle', 'r', g.zoomInfo.pointSize / step);
    util.changeStyle('svg circle', 'stroke-width', 2 / step);
}

export function init() {
    if (!g.svg) {
        g.svg = {
            svg: document.getElementById('svg_overlay'),
            iso: document.getElementById('svg_iso'),
            top: document.getElementById('svg_top'),
            defs: document.getElementById('svg_defs'),
        };
    }
    g.svg.iso.innerHTML = '';
    g.svg.top.innerHTML = '';
    g.svg.defs.innerHTML = '';
}

export function debug() {
    if (g.query_string.debug) {
        const points = [[7936, 11264], [8192, 11264], [8192, 11520], [7936, 11520]];
        const holes = [[[8000, 11328], [8128, 11328], [8128, 11456], [8000, 11456]]];
        newPolygon('debug_polygon', points, holes, 'cyan', 'none');
        text('debug_text', { color: 'cyan', font: 'fantasy', layer: 0 }, { x: 8064, y: 11400, text: 'Debug Text' });
        point('debug_point', { layer: 0}, { x: 8064, y: 11400 });
    }
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

function newPolygon(id, points, masks, color, background) {
    const defs = g.svg.defs.appendChild(newSVGElement('g', id));
    defs.appendChild(newPath(id + '_p', points));
    const maskIds = [];
    if (masks && masks.length > 0) {
        for (let i = 0; i < masks.length; i++) {
            const maskId = id + '_p_' + i;
            defs.appendChild(newPath(maskId, masks[i]));
            maskIds.push(maskId);
        }
        defs.appendChild(newMask(id + '_m', id + '_p', maskIds));
    } else {
        defs.appendChild(newClip(id + '_c', id + '_p'));
    }
    const attrs = {
        href: '#' + id + '_p',
        stroke: color,
        fill: background,
    };
    if (maskIds.length > 0) {
        attrs['mask'] = 'url(#' + id + '_m)';
    } else {
        attrs['clip-path'] = 'url(#' + id + '_c)';
    }
    const container = g.svg[g.map_type].appendChild(newSVGElement('g', id + '_u'));
    container.appendChild(newSVGElement('use', null, attrs));
    for (const maskId of maskIds) {
        container.appendChild(newSVGElement('use', null, {
            href: '#' + maskId,
            stroke: color,
            mask: 'url(#' + id + '_m)',
        }));
    }
}

function text(id, mark, part) {
    const { x, y } = part;
    const layer = mark.layer || 0;
    const fill = part.color || mark.color || 'white';
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
    const e = newSVGElement('text', id, attrs);
    e.textContent = part.text;
    if (mark.font) e.style['font-family'] = mark.font;
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
    }
    g.svg.top.appendChild(e);
}

function point(id, mark, part) {
    const { x, y } = part;
    const { color, background } = mark;
    const layer = mark.layer || 0;
    const attrs = { cx: x + 0.5, cy: y + 0.5 };
    if (g.map_type === 'iso') {
        attrs.cx = (x - y) / 2;
        attrs.cy = (x + y + 1 - layer * 6) / 4;
    }
    const e = newSVGElement('circle', id, attrs);
    g.svg.top.appendChild(e);
    if (color) e.style.stroke = color;
    if (background) e.style.fill = background;
}

function shiftPoints(points, layer) {
    const d = -layer * 3;
    return points.map(p => ({ x: p.x + d, y: p.y + d }));
}

function polygon(id, mark, part) {
    const color = mark.color || '#39f';
    const background = mark.background || 'none';
    const layer = mark.layer || 0;
    let points = part.points;
    let masks = part.masks;
    if (g.map_type === 'iso' && layer !== 0) {
        points = shiftPoints(part.points, layer);
        if (masks && masks.length > 0) {
            masks = masks.map(mask => shiftPoints(mask, layer));
        }
    }
    newPolygon(id, points, masks, color, background);
}

function polyline(id, mark, part) {
    const color = mark.color || '#39f';
    const layer = mark.layer || 0;
    const { width, linecap, linejoin } = part;
    let points = part.points;
    if (g.map_type === 'iso' && layer !== 0) {
        points = shiftPoints(part.points, layer);
    }
    const e = newPath(id, points, false);
    g.svg[g.map_type].appendChild(e);
    e.setAttribute('stroke', color);
    e.setAttribute('fill', 'none');
    if (width) e.setAttribute('stroke-width', width);
    if (linecap) e.setAttribute('stroke-linecap', linecap);
    if (linejoin) e.setAttribute('stroke-linejoin', linejoin);
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
    removed += remove(id + '_u');
    removed += remove(id);
    return removed > 0;
}

export function removeMark(id) {
    return true;
}