import * as c from "../coordinates.js";
import { g } from "../globals.js";
import { getNeighbours, calcMissingBorderRatio } from "../algorithm/geometry/rects_intersection.js";

export function updateZoom() {
    util.changeStyle('div.point', 'width', g.zoomInfo.pointSize + 'px');
    util.changeStyle('div.point', 'height', g.zoomInfo.pointSize + 'px');
    util.changeStyle('div.point.text', 'padding-top', (g.zoomInfo.pointSize >> 1) + 'px');
    util.changeStyle('div.area.rect.iso', 'border-width', g.zoomInfo.rectBorder + 'px');
    util.changeStyle('div.area.rect.top', 'border-width', (g.zoomInfo.rectBorder >> 1) + 'px');
    util.changeStyle('div.area.rect.diff-sum.iso', 'border-width', (g.zoomInfo.rectBorder >> 1) + 'px');
    util.changeStyle('div.text', 'font-size', g.zoomInfo.fontSize);
}

var needRefresh = false;

function setClass(element, mark, part) {
    //element.className = "";
    element.setAttribute('class', '');
    element.classList.add('mark');
    element.classList.add(g.map_type);
    element.classList.add(part.shape);
    element.classList.add(mark.type);
    if (mark.layer > g.currentLayer) {
        element.classList.add('above');
    }
    if (mark.layer < g.currentLayer) {
        element.classList.add('below');
    }
    if (mark.cls) {
        for (const c of mark.cls) {
            element.classList.add(c);
        }
    }
    if (part.cls) {
        for (const c of part.cls) {
            element.classList.add(c);
        }
    }
    if (mark.selected) {
        element.classList.add('selected');
    }
    if (part.shape === 'rect' && part.selected) {
        element.classList.add('selected-rect');
    }
    if (mark.interactive) {
        element.classList.add('interactive');
    } else {
        element.classList.add('passthrough');
    }
}

function buildLinerBorder(segments, dir, color, size) {
    const result = [`linear-gradient(${dir}`, `${color} 0%`];
    for (const [y0, y1] of segments) {
        if (y0 > 0) {
            result.push(`${color} calc(${y0 * 100}% + ${size})`);
            result.push(`transparent calc(${y0 * 100}% + ${size})`);
        } else {
            result.push(`${color} ${y0 * 100}%`);
            result.push(`transparent ${y0 * 100}%`);
        }
        if (y1 < 1) {
            result.push(`transparent calc(${y1 * 100}% - ${size})`);
            result.push(`${color} calc(${y1 * 100}% - ${size})`);
        } else {
            result.push(`transparent ${y1 * 100}%`);
            result.push(`${color} ${y1 * 100}%`);
        }
    }
    result.push(`${color} 100%)`);
    return result.join(', ');
}

function setBorder(element, rect, color, borderSize, bgColor) {
    const { top, bottom, left, right } = rect.border;
    const background = [];
    background.push(buildLinerBorder(top, '90deg', color, borderSize));
    background.push(buildLinerBorder(bottom, '90deg', color, borderSize));
    background.push(buildLinerBorder(left, '180deg', color, borderSize));
    background.push(buildLinerBorder(right, '180deg', color, borderSize));
    background.push(bgColor);
    element.style.border = 'none';
    element.style.background = background.join(', ');
    element.style['background-repeat'] = 'no-repeat, no-repeat, no-repeat, no-repeat';
    element.style['background-size'] = `100% ${borderSize}, 100% ${borderSize}, ${borderSize} 100%, ${borderSize} 100%`;
    element.style['background-position'] = '0px 0px, 0px 100%, 0px 0px, 100% 0px';
}

function getCalculatedClassStyle(element, keys) {
    const e = document.createElement('div');
    e.className = element.className + ' resolved';
    e.style.display = 'none';
    document.body.appendChild(e);
    const computed = window.getComputedStyle(e);
    const style = {};
    for (const key of keys) {
        style[key] = computed.getPropertyValue(key);
    }
    document.body.removeChild(e);
    return style;
}

function newSVGElement(type, id=null) {
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, type);
    if (id) {
        svg.setAttribute("id", id);
    }
    return svg;
}

function upsertOverlay(id, type, pos, placement, drawFunc) {
    let element = document.getElementById(id);
    if (element) {
        g.viewer.updateOverlay(element, pos, placement); // no drawFunc
        needRefresh = false;
    } else {
        if (type === 'svg') {
            element = newSVGElement(type, id);
        } else {
            element = document.createElement(type);
            element.id = id;
        }
        g.viewer.addOverlay(element, pos, placement, drawFunc);
        needRefresh = true;
    }
    return element;
}

function drawRect(mark, part, position, size, element) {
    const wrapper = element.parentElement;
    wrapper.style.left = position.x + 'px';
    wrapper.style.top = position.y + 'px';
    wrapper.style['pointer-events'] = 'none';
    element.style.width = size.x + 'px';
    element.style.height = size.y + 'px';
    if (g.map_type === 'iso' && mark.isDiffSum) {
        element.style.width = (size.x / 2) + 'px';
        element.style.height = (size.y / 4) + 'px';
    }
    let color = mark.color || undefined;
    let background = mark.background || undefined;
    if (part.border) {
        let borderSize = g.zoomInfo.rectBorder || 8;
        if (g.map_type === 'top' || mark.isDiffSum) {
            borderSize = borderSize >> 1;
        }
        if (!color || !background) {
            const style = getCalculatedClassStyle(element, ['border-color', 'background-color']);
            color = color || style['border-color'];
            background = background || style['background-color'];
        }
        setBorder(element, part, color, borderSize + 'px', background);
    } else {
        if (color) {
            element.style['border-color'] = color;
        }
        if (background) {
            element.style['background-color'] = background;
        }
    }
}

function rect(id, mark, part) {
    let { x, y, width, height } = part;
    if (mark.isDiffSum) {
        x = (part.x + part.y) / 2;
        y = (part.y - part.x) / 2;
    }
    const vp = c.getViewportPointBySquare(g.viewer, g.base_map, x, y, mark.layer);
    const step = g.viewer.world.getItemAt(0).imageToViewportCoordinates(g.base_map.sqr, 0).x;
    const r = new OpenSeadragon.Rect(vp.x, vp.y, step * width, step * height);
    const placement = OpenSeadragon.Placement.TOP_LEFT;
    const element = upsertOverlay(id, 'div', r, placement, drawRect.bind(null, mark, part));
    setClass(element, mark, part);
    element.style.display = 'block';
    element.title = mark.name || '';
}

function drawPoint(mark, part, position, size, element) {
    const wrapper = element.parentElement;
    wrapper.style.left = position.x + 'px';
    wrapper.style.top = position.y + 'px';
    wrapper.style['pointer-events'] = 'none';
}

function point(id, mark, part) {
    const { x, y } = part;
    const vp = c.getViewportPointBySquare(g.viewer, g.base_map, x + 0.5, y + 0.5, mark.layer);
    const point = new OpenSeadragon.Point(vp.x, vp.y);
    const placement = OpenSeadragon.Placement.CENTER;
    const element = upsertOverlay(id, 'div', point, placement, drawPoint.bind(null, mark, part));
    setClass(element, mark, part);
    element.style.display = 'block';
    element.title = mark.name || '';
    if (mark.color) {
        element.style['border-color'] = mark.color;
    }
    if (mark.background) {
        element.style['background-color'] = mark.background;
    }
}

function drawText(mark, part, position, size, element) {
    const wrapper = element.parentElement;
    wrapper.style.left = position.x + 'px';
    wrapper.style.top = position.y + 'px';
    wrapper.style['pointer-events'] = 'none';
    wrapper.style['z-index'] = 10;
}

function text(id, mark, part) {
    const { x, y, text } = part;
    const vp = c.getViewportPointBySquare(g.viewer, g.base_map, x + 0.5, y + 0.5, mark.layer);
    const point = new OpenSeadragon.Point(vp.x, vp.y);
    const placement = OpenSeadragon.Placement[part.placement] || OpenSeadragon.Placement.TOP;
    const element = upsertOverlay(id, 'div', point, placement, drawText.bind(null, mark, part));
    setClass(element, mark, part);
    if (part.font || mark.font) {
        element.style.font = part.font || mark.font;
    }
    const color = part.color || mark.color;
    if (color) {
        element.style.color = color;
        if (util.isLightColor(color)) {
            element.classList.add('light');
        }
    }
    element.style.display = 'block';
    element.style['pointer-events'] = 'none';
    element.style['background-color'] = 'rgba(0,0,0,0)';
    element.style.border = 'none';
    element.innerHTML = text.replaceAll('\n', '<br/>');
}

function drawSVG(mark, part, position, size, element) {
    const wrapper = element.parentElement;
    wrapper.style.left = position.x + 'px';
    wrapper.style.top = position.y + 'px';
    wrapper.style['pointer-events'] = 'none';
    element.style.width = size.x + 'px';
    element.style.height = size.y + 'px';
}

function svg(id, mark, part) {
    const { points, shape, width, linecap, linejoin } = part;
    const x = Math.min(...points.map(p => p.x)) - width;
    const y = Math.min(...points.map(p => p.y)) - width;
    const maxX = Math.max(...points.map(p => p.x)) + width;
    const maxY = Math.max(...points.map(p => p.y)) + width;
    const vp = c.getViewportPointBySquare(g.viewer, g.base_map, x, y, mark.layer);
    const step = g.viewer.world.getItemAt(0).imageToViewportCoordinates(g.base_map.sqr, 0).x;
    const r = new OpenSeadragon.Rect(vp.x, vp.y, step * (maxX - x), step * (maxY - y));
    const placement = OpenSeadragon.Placement.TOP_LEFT;
    const element = upsertOverlay(id, 'svg', r, placement, drawSVG.bind(null, mark, part));
    setClass(element, mark, part);
    element.style['pointer-events'] = 'none';
    element.setAttribute('viewBox', `0 0 ${maxX - x} ${maxY - y}`);
    let gElement = document.getElementById(id + '-g');
    if (!gElement) {
        gElement = newSVGElement('g', id + '-g');
        element.appendChild(gElement);
    }
    let e = document.getElementById(id + '-path');
    if (!e) {
        e = newSVGElement(shape, id + '-path');
        gElement.appendChild(e);
    }
    if (shape === 'polygon' || shape === 'polyline') {
        const elementPoints = [];
        for (const p of points) {
            const dx = p.x - x;
            const dy = p.y - y;
            elementPoints.push(dx + ',' + dy);
        }
        if (shape === 'polygon') {
            e.setAttribute('fill', mark.background || 'none');
            e.setAttribute('stroke', mark.color || 'none');
        } else {
            e.setAttribute('fill', 'none');
            e.setAttribute('stroke', mark.color || 'white');
        }
        e.setAttribute('points', elementPoints.join(' '));
        e.setAttribute('stroke-width', width);
        if (linecap) e.setAttribute('stroke-linecap', linecap);
        if (linejoin) e.setAttribute('stroke-linejoin', linejoin);
    }
}

function processArea(id, mark) {
    const rects = mark.parts.filter(part => part.shape === 'rect');
    const neighbours = getNeighbours(rects, { noCorner: true });
    for (let i = 0; i < rects.length; i++) {
        const rect = rects[i];
        const neighbourIndexes = neighbours[i];
        if (neighbourIndexes.length === 0) continue;
        // render rect not polygon, no need to consider priority
        rect.border = calcMissingBorderRatio(rect, [], neighbourIndexes.map(j => rects[j]));
    }
}

var _PROCESS_FUNCTIONS = {
    area: processArea
};

var _DRAW_FUNCTIONS = {
    rect: rect,
    point: point,
    text: text,
    polygon: svg,
    polyline: svg,
};

export function addPart(id, mark, part) {
    const func = _DRAW_FUNCTIONS[part.shape]
    if (func) {
       func(id, mark, part);
    }
}

export function addMark(id, mark) {
    const func = _PROCESS_FUNCTIONS[mark.type]
    if (func) {
        func(id, mark);
    }
    return true;
}

export function removePart(id) {
    const element = document.getElementById(id);
    if (element) {
        g.viewer.removeOverlay(element);
        needRefresh = false;
    }
}

export function removeMark(id) {
    return true;
}

export function refresh() {
    if (needRefresh) {
        addPart('_osd_draw_dummy', { layer: 0 }, { shape: 'point', x: 0, y: 0 });
        removePart('_osd_draw_dummy');
    }
}