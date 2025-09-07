import { g } from "./globals.js";
import { lineClip } from "./algorithm/geometry/geometry_utils.js";

var CELL_FONT = '12pt bold monospace';
var BLOCK_FONT = '12pt monospace';
var CELL_COLOR = 'yellow';
var BLOCK_COLOR = 'lime';
var MIN_CELL_STEP = 8;
var MIN_BLOCK_STEP = 8;
var TEXT_PADDING = 8;
var ISO_MIN_STEP_SCALE = 2;

function textSize(ctx, font, text) {
    const old_font = ctx.font;
    ctx.font = font;
    const m = ctx.measureText('-01234,56789');
    const ascent = m.actualBoundingBoxAscent;
    const descent = m.actualBoundingBoxDescent;
    const width = ctx.measureText(text).width;
    ctx.font = old_font;
    return [width, ascent, descent];
}

function grid2keyTop(gx, gy) {
    return [gx, gy];}

function grid2keyIso(gx, gy) {
    return [(gx + gy) / 2, (gy - gx) / 2];
}

var grid2key = {
    'iso': grid2keyIso,
    'top': grid2keyTop
};

// return square(0, 0, layer) on canvas coordinate.
function getCanvasOrigin(viewer, map, layer) {
    const vp00 = getViewportPointBySquare(viewer, map, 0, 0, layer);
    const c00 = viewer.viewport.pixelFromPoint(vp00, true);
    c00.x *= window.devicePixelRatio;
    c00.y *= window.devicePixelRatio;
    return c00;
}

function getSquareStep(viewer, map, current) {
    return map.sqr * getZoom(viewer, current) / map.scale;
}

function toTopSquare(step, x, y, layer, round) {
    const coord = [x/step, y/step]
    if (round) {
        return coord.map(Math.floor);
    }
    return coord;
}

function fromTopSquare(step, sx, sy, layer) {
    return [sx*step, sy*step];
}

function toIsoSquare(step, x, y, layer, round) {
    const fgx = x / step;
    const fgy = 2 * (y + 1.5 * layer * step) / step;
    const sx = fgy + fgx;
    const sy = fgy - fgx;
    if (round) {
        return [Math.floor(sx), Math.floor(sy)];
    }
    return [sx, sy];
}

function fromIsoSquare(step, sx, sy, layer) {
    const x = (sx - sy) * step / 2;
    const y = (sx + sy) * step / 4 - 1.5 * layer * step;
    return [x, y];
}

var toSquare = {
    iso: toIsoSquare,
    top: toTopSquare
}

var fromSquare = {
    iso: fromIsoSquare,
    top: fromTopSquare
}

function inScreenCoords(ctx, map_type, c00, step, border) {
    const w = ctx.canvas.width;
    const h = ctx.canvas.height;
    let step_x = step;
    let step_y = step;
    let y_start = 0;
    let y_inc = 1;
    if (map_type != 'top') {
        step_x = step / 2;
        step_y = step / 4;
        y_inc = 2;
    }

    const gx0 = -Math.floor(c00.x / step_x) - border;
    //const cx0 = c00.x + (gx0 * step_x);
    const gy0 = -Math.floor(c00.y / step_y) - border;
    //const cy0 = c00.y + (gy0 * step_y);
    const dx0 = gx0 + gy0;
    //const dy0 = gy0 - gx0;

    const coords = [];
    for (let x = 0; x <= w / step_x + border * 2 - 1; x++) {
        if (map_type != 'top') {
            y_start = (dx0 + x) % 2;
        }
        for (let y = y_start; y <= h / step_y + border * 2 - 1; y+=y_inc) {
            const gx = gx0 + x;
            const gy = gy0 + y;
            const [kx, ky] = grid2key[map_type](gx, gy);
            coords.push([gx, gy, kx, ky]);
        }
    }
    return coords;
}

export function zoomTo(sx, sy, layer, step) {
    const vp = getViewportPointBySquare(g.viewer, g.base_map, sx, sy, layer);
    g.viewer.viewport.panTo(vp, true).zoomTo(stepToZoom(step), vp);
    if (g.currentLayer !== layer) {
        const selectElement = document.getElementById('layer_selector');
        selectElement.value = layer;
        selectElement.dispatchEvent(new Event('change'));
    }
}

class Range {
    constructor(viewer, map, current=true) {
        const c00 = getCanvasOrigin(viewer, map, 0);
        const step = getSquareStep(viewer, map, current);
        const w = viewer.drawer.context.canvas.width;
        const h = viewer.drawer.context.canvas.height;
        const [x0, y0] = toSquare[map.type](step, -c00.x, -c00.y, 0, false);
        const [x1, y1] = toSquare[map.type](step, -c00.x + w, -c00.y + h, 0, false);
        if (map.type == 'top') {
            this.diffSum = false;
            this._initXY(x0, y0, x1 + 1, y1 + 1);
        } else {
            this.diffSum = true;
            this._initDiffSum(x0, y0, x1 + 1, y1 + 1);
        }
    }

    _initXY(x0, y0, x1, y1) {
        this.minX = x0;
        this.minY = y0;
        this.maxX = x1;
        this.maxY = y1;
        this.centerX = (x0 + x1) / 2;
        this.centerY = (y0 + y1) / 2;
    }

    _initDiffSum(x0, y0, x1, y1) {
        // top-left corner: (x0, y0)
        // top-right corner:
        //     ((x0 + x1 + y0 - y1) /2, (x0 - x1 + y0 + y1) / 2)
        // bottom-left corner:
        //     ((x0 + x1 - y0 + y1) / 2, (-x0 + x1 + y0 + y1) / 2)
        // bottom-right corner: (x1, y1)
        this.minX = x0;
        this.minY = ((x0 - x1 + y0 + y1) / 2);
        this.maxX = x1;
        this.maxY = ((-x0 + x1 + y0 + y1 + 1) / 2);
        this.minDiff = x0 - y0;
        this.maxDiff = x1 - y1;
        this.minSum = x0 + y0;
        this.maxSum = x1 + y1;
        this.centerX = (x0 + x1) / 2;
        this.centerY = (y0 + y1) / 2;
    }

    intersects(mark) {
        if (this.diffSum) {
            return this._intersectsDiffSumBox(mark.bboxDiffSum(), mark.layer);
        } else {
            return this._intersectsBox(mark.bbox());
        }
    }

    _intersectsBox(target) {
        const { minX, minY, maxX, maxY } = target;
        const xmin = minX > this.minX ? minX : this.minX;
        const xmax = maxX < this.maxX ? maxX : this.maxX;
        const ymin = minY > this.minY ? minY : this.minY;
        const ymax = maxY < this.maxY ? maxY : this.maxY;
        return (xmin <= xmax && ymin <= ymax);
    }

    _intersectsDiffSumBox(target, layer = 0) {
        const d = this.diffSum ? layer * 6 : 0;
        const { minDiff, maxDiff, minSum, maxSum } = target;
        const dmin = minDiff > this.minDiff ? minDiff : this.minDiff;
        const dmax = maxDiff < this.maxDiff ? maxDiff : this.maxDiff;
        const smin = minSum - d > this.minSum ? minSum - d : this.minSum;
        const smax = maxSum - d < this.maxSum ? maxSum - d : this.maxSum;
        return (smin <= smax && dmin <= dmax);
    }

    contains(x, y, layer = 0) {
        if (this.diffSum) {
            const diff = x - y;
            const sum = x + y - layer * 6;
            return this._containsDiffSum(diff, sum);
        } else {
            return this._containsXY(x, y);
        }

    }

    _containsXY(x, y) {
        return (x >= this.minX && x <= this.maxX && y >= this.minY && y <= this.maxY);
    }

    _containsDiffSum(diff, sum) {
        return (diff >= this.minDiff && diff <= this.maxDiff && sum >= this.minSum && sum <= this.maxSum);
    }

    getBound(minLayer = null, maxLayer = null) {
        if (minLayer === null) minLayer = g.base_map.minlayer;
        if (maxLayer === null) maxLayer = g.base_map.maxlayer;
        if (this.diffSum) {
            const d0 = maxLayer * 3;
            const d1 = minLayer * 3;
            //return this;
            return {
                minDiff: this.minDiff,
                maxDiff: this.maxDiff,
                minSum: this.minSum - d0 * 2,
                maxSum: this.maxSum - d1 * 2,
            };
        } else {
            return this;
        }
    }

    segmentClip(x0, y0, x1, y1) {
        // return [xa, ya, xb, yb] where segment (a, b) is the part in range
        // return null if segment is out of range
        if (this.diffSum) {
            const diff0 = x0 - y0;
            const sum0  = x0 + y0;
            const diff1 = x1 - y1;
            const sum1  = x1 + y1;
            const result = lineClip(diff0, sum0, diff1, sum1, this.minDiff, this.minSum, this.maxDiff, this.maxSum);
            if (result) {
                const [diffa, suma, diffb, sumb] = result;
                const xa = (suma + diffa) / 2;
                const ya = (suma - diffa) / 2;
                const xb = (sumb + diffb) / 2;
                const yb = (sumb - diffb) / 2;
                return [xa, ya, xb, yb];
            } else {
                return null;
            }
        } else {
            return lineClip(x0, y0, x1, y1, this.minX, this.minY, this.maxX, this.maxY);
        }
    }
}

export function getCanvasRange(current) {
    return new Range(g.viewer, g.base_map, current);
}

function getSquareByCanvas(viewer, map, x, y, layer) {
    //const x = event.position.x * window.devicePixelRatio;
    //const y = event.position.y * window.devicePixelRatio;
    const c00 = getCanvasOrigin(viewer, map, 0);
    const step = getSquareStep(viewer, map, true);
    const [sx, sy] = toSquare[map.type](step, x - c00.x, y - c00.y, layer, true);
    return [sx, sy];
}

export function getZoom(viewer, current) {
    let zoom = viewer.viewport.getZoom(current);
    zoom = viewer.world.getItemAt(0).viewportToImageZoom(zoom);
    zoom *= window.devicePixelRatio;
    return zoom;
}

export function isMaxZoom(viewer, current) {
    let zoom = viewer.viewport.getZoom(current);
    zoom = viewer.world.getItemAt(0).viewportToImageZoom(zoom);
    const maxZoom = viewer.viewport.getMaxZoomPixelRatio();
    const EPS = 1e-10;
    return zoom + EPS >= maxZoom;
}

export function stepToZoom(step) {
    // step == pixels per square
    const zoom = g.viewer.world.getItemAt(0).imageToViewportZoom(step / g.base_map.sqr);
    return zoom / window.devicePixelRatio;
}

export function getSquare(event) {
    const x = event.position.x * window.devicePixelRatio;
    const y = event.position.y * window.devicePixelRatio;
    return getSquareByCanvas(g.viewer, g.base_map, x, y, g.currentLayer);
}

export function getViewportPointBySquare(viewer, map, x, y, layer) {
    const [dx, dy] = fromSquare[map.type](map.sqr, x, y, layer);
    const imgx = (map.x0 + dx) / map.scale;
    const imgy = (map.y0 + dy) / map.scale;
    return viewer.world.getItemAt(0).imageToViewportCoordinates(imgx, imgy);
}

export function makeKey(x, y) {
    return x + ',' + y;
}

export class Grid {
    constructor(base_map) {
        this.map = base_map;
        this.step = 0;
        this.cell_step = 0;
        this.block_step = 0;
        this.cell = 0; // cell line thickness
        this.block = 0; // block line thickness
        this.size = {
            cell: base_map.cell_size,
            block: base_map.block_size,
            sqr: 1
        };
        this.blocks_per_cell = base_map.cell_in_block ** 2;
    }

    update(viewer) {
        this.c00 = getCanvasOrigin(viewer, this.map, 0);
        const step = getSquareStep(viewer, this.map, true);
        if (this.step === step) {
            return false;
        }
        this.step = step;
        this.block_step = this.step * this.size.block;
        this.cell_step = this.step * this.size.cell;
        const scale = this.map.type == 'top' ? 1 : ISO_MIN_STEP_SCALE;
        if (this.block_step >= MIN_BLOCK_STEP * scale * window.devicePixelRatio) {
            this.block = 1;
            this.cell = 3;
        } else {
            if (this.cell_step >= MIN_CELL_STEP * scale * window.devicePixelRatio) {
                this.cell = 1;
                this.block = 0;
            } else {
                this.cell = 0;
                this.block = 0;
            }
        }
        this.ctx = viewer.drawer.context;
        this.updateTextSize();
        return true;
    }

    updateTextSize() {
        const [cell_width, cell_ascent, cell_descent] = textSize(this.ctx, CELL_FONT, '-00,-00');
        const cell_height = cell_ascent + cell_descent;
        const [block_width, block_ascent, block_descent] = textSize(this.ctx, BLOCK_FONT, '-0000,-0000');
        const block_height = block_ascent + block_descent;
        if (this.map.type == 'top') {
            this.cell_text_min_step = TEXT_PADDING + Math.max(cell_width, cell_height);
            this.cell_text_offset = TEXT_PADDING / 2 + cell_ascent;
            this.block_text_min_step = TEXT_PADDING + Math.max(block_width, block_height + cell_height + TEXT_PADDING / 4);
        } else {
            this.cell_text_min_step = TEXT_PADDING + cell_width + 2 * cell_height;
            this.cell_text_offset = (TEXT_PADDING + cell_width) / 4 + cell_ascent;
            if (block_width > cell_width) {
                this.block_text_min_step = TEXT_PADDING + block_width + 2 * (block_height + Math.max(0, cell_height - (block_width - cell_width) / 4));
            } else {
                this.block_text_min_step = TEXT_PADDING + cell_width + 2 * (cell_height + Math.max(0, block_height - (cell_width - block_width) / 4));
            }
        }
        this.block_text_offset = this.cell_text_offset + cell_descent + block_ascent + TEXT_PADDING / 4;
    }

    convertCoord(f, t, x, y) {
        const fs = this.size[f];
        const ts = this.size[t];
        return [Math.floor(x * fs / ts), Math.floor(y * fs / ts)]
    }

    drawEditState(trimmer, layer) {
        const fill = this.ctx.fillStyle;
        let step = this.cell_step;
        if (this.block) {
            step = this.block_step;
        }
        const [l00, step_x, step_y] = this.layerOriginAndStep(step, layer);
        const coords = inScreenCoords(this.ctx, this.map.type, l00, step, 2);

        if (this.map.type == 'top') {
            this.ctx.setTransform(1, 0, 0, 1, l00.x, l00.y);
        } else {
            this.ctx.setTransform(0.5, 0.25, -0.5 ,0.25, l00.x, l00.y);
        }
        let color = 0;
        for (const [gx, gy, kx, ky] of coords) {
            const key = makeKey(kx, ky);
            if ((this.block && trimmer.selected_blocks.has(key)) ||
                (!this.block && trimmer.selected_cells[key] > 0 && trimmer.selected_cells[key] == trimmer.saved_cells[key])) {
                color = 'rgba(255,0,0,0.5)'; // full selected, red
            } else if (!this.block && trimmer.selected_cells[key] > 0) {
                color = 'rgba(255,255,0,0.5)'; // partial selected cell, yellow
            } else if ((this.block && trimmer.saved_blocks.has(key)) ||
                       (!this.block && trimmer.saved_cells[key] == this.blocks_per_cell)) {
                color = 'rgba(0,255,0,0.5)'; // full saved, green
            } else if (!this.block && trimmer.saved_cells[key] > 0) {
                color = 'rgba(0,0,255,0.5)'; // partial saved cell, blue
            } else {
                color = 0;
            }
            if (color) {
                this.ctx.fillStyle = color;
                this.ctx.fillRect(kx * step, ky * step, step, step);
            }
        }
        // drag selecting area
        if (trimmer.selecting && (trimmer.start.x != trimmer.end.x || trimmer.start.y != trimmer.end.y)) {
            const size = this.size[trimmer.selecting];
            const xmin = Math.min(trimmer.end.x, trimmer.start.x);
            const ymin = Math.min(trimmer.end.y, trimmer.start.y);
            const xmax = Math.max(trimmer.end.x, trimmer.start.x) + size;
            const ymax = Math.max(trimmer.end.y, trimmer.start.y) + size;
            const [xs, ys] = this.convertCoord('sqr', trimmer.selecting, xmin, ymin);
            const [xe, ye] = this.convertCoord('sqr', trimmer.selecting, xmax, ymax);

            this.ctx.fillStyle = 'rgba(255,255,255,0.5)'; // white, semi-transparent
            this.ctx.fillRect(xs * this.step * size, ys * this.step * size, (xe - xs) * this.step * size, (ye - ys) * this.step * size);
        }

        this.ctx.setTransform();
        this.ctx.fillStyle = fill;
    }

    drawGrid(step, color, line_width, layer) {
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = line_width;
        const w = this.ctx.canvas.width;
        const h = this.ctx.canvas.height;
        let x1 = this.c00.x
        let y1 = this.c00.y
        let max_w = w;
        let min_h = 0;
        let x_shift = 0;
        let y_shift = 0;
        let y_step = step;
        if (this.map.type != 'top') {
            const layer_shift = 1.5 * this.step * layer;
            x1 += 2 * (this.c00.y - layer_shift);
            y1 -= this.c00.x / 2 + layer_shift;
            max_w += 2 * h;
            min_h -= w / 2;
            x_shift = -2 * h;
            y_shift = w / 2;
            y_step = step / 2;
        }
        this.ctx.beginPath();
        x1 -= Math.floor(x1 / step) * step;
        while (x1 <= max_w) {
            this.ctx.moveTo(x1, 0);
            this.ctx.lineTo(x1 + x_shift, h);
            x1 += step;
        }
        y1 += Math.ceil((h - y1) / step) * step;
        while (y1 >= min_h) {
            this.ctx.moveTo(0, y1);
            this.ctx.lineTo(w, y1 + y_shift);
            y1 -= y_step;
        }
        this.ctx.stroke();
    }

    layerOriginAndStep(step, layer) {
        let [step_x, step_y] = [step, step];
        let l00 = { x: this.c00.x, y: this.c00.y };
        if (this.map.type != 'top') {
            [step_x, step_y] = [step / 2, step / 4];
            l00 = { x: this.c00.x, y: this.c00.y - 1.5 * layer * this.step };
        }
        return [l00, step_x, step_y];
    }

    drawCoord(step, yoffset, color, font, layer) {
        this.ctx.fillStyle = color;
        this.ctx.font = font;
        const [l00, step_x, step_y] = this.layerOriginAndStep(step, layer);
        const coords = inScreenCoords(this.ctx, this.map.type, l00, step, 1);
        let xoffset = TEXT_PADDING / 2;
        this.ctx.setTransform(1, 0, 0, 1, l00.x, l00.y);
        for (const [gx, gy, kx, ky] of coords) {
            const cx = gx * step_x;
            const cy = gy * step_y;
            const text = makeKey(kx, ky);
            if (this.map.type != 'top') {
                xoffset = - this.ctx.measureText(text).width / 2;
            }
            this.ctx.fillText(text, cx + xoffset, cy + yoffset);

        }
        this.ctx.setTransform();
    }


    draw(layer) {
        const stroke = this.ctx.strokeStyle;
        const fill = this.ctx.fillStyle;
        const font = this.ctx.font;

        if (this.block) {
            this.drawGrid(this.block_step, BLOCK_COLOR, this.block, layer);
        }

        if (this.block_step >= this.block_text_min_step) {
            this.drawCoord(this.block_step, this.block_text_offset, BLOCK_COLOR, BLOCK_FONT, layer);
        }

        if (this.cell) {
            this.drawGrid(this.cell_step, CELL_COLOR, this.cell, layer);
        }

        if (this.cell_step >= this.cell_text_min_step) {
            this.drawCoord(this.cell_step, this.cell_text_offset, CELL_COLOR, CELL_FONT, layer);
        }

        this.ctx.strokeStyle = stroke;
        this.ctx.fillStyle = fill;
        this.ctx.font = font;
    }
}
