import * as c from "../coordinates.js";
import { g } from "../globals.js";
import { getNeighbours, calcBorder } from "../algorithm/geometry/rects_intersection.js";

function setClass(element, mark, part) {
    element.className = "";
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

function drawRect(mark, part, position, size, element) {
    const wrapper = element.parentElement;
    wrapper.style.left = position.x + 'px';
    wrapper.style.top = position.y + 'px';
    wrapper.style['pointer-events'] = 'none';
    element.style.width = size.x + 'px';
    element.style.height = size.y + 'px';
    let color = mark.color || undefined;
    let background = mark.background || undefined;
    if (part.border) {
        let borderSize = g.zoomInfo.rectBorder || 8;
        if (g.base_map.type === 'top') {
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
    const { x, y, width, height } = part;
    const vp = c.getViewportPointBySquare(g.viewer, g.base_map, x, y, mark.layer);
    const step = g.viewer.world.getItemAt(0).imageToViewportCoordinates(g.base_map.sqr, 0).x;
    const r = new OpenSeadragon.Rect(vp.x, vp.y, step * width, step * height);
    const placement = OpenSeadragon.Placement.TOP_LEFT;
    let element = document.getElementById(id);
    if (element) {
        g.viewer.updateOverlay(element, r, placement);
    } else {
        element = document.createElement('div');
        element.id = id;
        g.viewer.addOverlay(element, r, placement, drawRect.bind(null, mark, part));
    }
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
    let element = document.getElementById(id);
    if (element) {
        g.viewer.updateOverlay(element, point, placement);
    } else {
        element = document.createElement('div');
        element.id = id;
        g.viewer.addOverlay(element, point, placement, drawPoint.bind(null, mark, part));
    }
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

}

function text(id, mark, part) {
    const { x, y, text } = part;
    const vp = c.getViewportPointBySquare(g.viewer, g.base_map, x + 0.5, y + 0.5, mark.layer);
    const point = new OpenSeadragon.Point(vp.x, vp.y);
    const placement = OpenSeadragon.Placement[part.placement] || OpenSeadragon.Placement.TOP;
    let element = document.getElementById(id);
    if (element) {
        g.viewer.updateOverlay(element, point, placement, drawText.bind(null, mark, part));
    } else {
        element = document.createElement('div');
        element.id = id;
        g.viewer.addOverlay(element, point, placement, drawText.bind(null, mark, part));
    }
    setClass(element, mark, part);
    element.style.font = mark.font || part.font || '12px Arial';
    if (mark.color) {
        element.style.color = mark.color;
    }
    element.style.display = 'block';
    element.style['pointer-events'] = 'none';
    element.style['background-color'] = 'rgba(0,0,0,0)';
    element.style.border = 'none';
    element.innerText = text;
}

var _DRAW_FUNCTIONS = {
    rect: rect,
    point: point,
    text: text
};

export function drawPart(id, mark, part) {
    const func = _DRAW_FUNCTIONS[part.shape]
    if (func) {
       func(id, mark, part);
    }
}

function processArea(mark) {
    const rects = mark.parts.filter(part => part.shape === 'rect');
    const neighbours = getNeighbours(rects, { noCorner: true });
    for (let i = 0; i < rects.length; i++) {
        const rect = rects[i];
        const neighbourIndexes = neighbours[i];
        if (neighbourIndexes.length === 0) continue;
        rect.border = calcBorder(rect, neighbourIndexes.map(j => rects[j]));
    }
}

var _PROCESS_FUNCTIONS = {
    area: processArea
}

export function processMark(mark) {
    const func = _PROCESS_FUNCTIONS[mark.type]
    if (func) {
        func(mark);
    }
}