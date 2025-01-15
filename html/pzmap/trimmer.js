import { g } from "./globals.js";
import * as c from "./coordinates.js";
import * as util from "./util.js";
import * as i18n from "./i18n.js";

function bkey2ckey(bkey) {
    let [bx, by] = bkey.split(',');
    return g.grid.convertCoord('block', 'cell', bx, by).join(',');
}

export class Trimmer {
    constructor() {
        this.save_path = '';
        this.save_version = '';
        this.selecting = 0;
        this.saved_blocks = new Set();
        this.saved_cells = {};
        this.selected_blocks = new Set();
        this.selected_cells = {};
    }

    clearSelection() {
        this.selecting = 0;
        this.saved_cells = {};
        this.saved_blocks.clear();
        this.selected_cells = {};
        this.selected_blocks.clear();
    }

    flip_block(bx, by) {
        let bkey = c.makeKey(bx, by);
        if (this.saved_blocks.has(bkey)) {
            let ckey = bkey2ckey(bkey);
            if (this.selected_blocks.has(bkey)) {
                this.selected_blocks.delete(bkey);
                this.selected_cells[ckey] -= 1;
                if (this.selected_cells[ckey] == 0) {
                    delete this.selected_cells[ckey];
                }
            } else {
                this.selected_blocks.add(bkey);
                if ( this.selected_cells[ckey] == undefined) {
                    this.selected_cells[ckey] = 0;
                }
                this.selected_cells[ckey] += 1;
            }
        }
    }

    flip_cell(cx, cy) {
        let ckey = c.makeKey(cx, cy);
        if (this.saved_cells[ckey] != undefined) {
            let op;
            if (this.selected_cells[ckey] == undefined || this.selected_cells[ckey] < this.saved_cells[ckey]) {
                this.selected_cells[ckey] = this.saved_cells[ckey];
                op = 'add';
            } else {
                delete this.selected_cells[ckey];
                op = 'delete';
            }
            let [bx0, by0] = g.grid.convertCoord('cell', 'block', cx, cy);
            let [bx1, by1] = g.grid.convertCoord('cell', 'block', cx + 1, cy + 1);
            for (let x = bx0; x < bx1; x++) {
                for (let y = by0; y < by1; y++) {
                    let bkey = c.makeKey(x, y);
                    if (this.saved_blocks.has(bkey)) {
                        this.selected_blocks[op](bkey);
                    }
                }
            }
        }
    }

    // canvas events
    press(event) {
        if (event.originalEvent.shiftKey) {
            let s = {};
            [s.x, s.y] = c.getSquare(event);
            this.start = s;
            this.end = s;
            if (g.grid.block) {
                this.selecting = 'block';
            } else if (g.grid.cell) {
                this.selecting = 'cell';
            }
            return true;
        }
        return false;
    }

    drag(event) {
        if (this.selecting) {
            let s = {};
            [s.x, s.y] = c.getSquare(event);
            this.end = s;
            if (!event.originalEvent.shiftKey) {
                this.selecting = 0;
            }
            return true;
        }
        return false;

    }

    release(event) {
        if (this.selecting) {
            if (event.originalEvent.shiftKey) {
                let s = {};
                [s.x, s.y] = c.getSquare(event);
                this.end = s;
                if (this.start.x != this.end.x || this.start.y != this.end.y) {
                    let [x1, y1] = g.grid.convertCoord('sqr', this.selecting, this.start.x, this.start.y);
                    let [x2, y2] = g.grid.convertCoord('sqr', this.selecting, this.end.x, this.end.y);
                    let xmin = Math.min(x1, x2); 
                    let xmax = Math.max(x1, x2); 
                    let ymin = Math.min(y1, y2); 
                    let ymax = Math.max(y1, y2); 
                    for (let x = xmin; x <= xmax; x++) {
                        for (let y = ymin; y <= ymax; y++) {
                            this['flip_' + this.selecting](x, y);
                        }
                    }
                }
            }
            this.selecting = 0;
            return true;
        }
        return false;

    }

    click(event) {
        let [sx, sy] = c.getSquare(event);
        let level = 'cell';
        if (g.grid.block && !event.originalEvent.shiftKey) {
            level = 'block';
        }
        let [x, y] = g.grid.convertCoord('sqr', level, sx, sy);
        this['flip_' + level](x, y);
        return true;
    }

    // ui events
    browse() {
        function ok(r) {
            util.setOutput('trimmer_output', 'green', i18n.T('TrimmerBrowserSuccess'), 3000);
            return Promise.resolve('');
        };

        function error(e) {
            util.setOutput('trimmer_output', 'red', i18n.T('TrimmerBrowserFailed', {error: e}), 5000);
            return Promise.resolve(e);
        };
        return window.fetch('./browse').then(ok).catch(error);
    }

    loadSave() {
        this.clearSelection();
        if (this.save_path) {
            let p = window.fetch('./load/' + this.save_path).then((r) => r.json());

            let load = (function (data) {
                this.save_version = data.version;
                if (this.save_version != g.base_map.pz_version) {
                    let args = {map_version: g.base_map.pz_version, save_version: this.save_version};
                    return Promise.reject(new Error(i18n.T('TrimmerVersionMismatch', args)));
                }
                let keys = data.blocks.split(';');
                for (let bkey of keys) {
                    this.saved_blocks.add(bkey);
                    let ckey = bkey2ckey(bkey);
                    if (this.saved_cells[ckey] == undefined) {
                        this.saved_cells[ckey] = 0;
                    }
                    this.saved_cells[ckey] += 1;
                }
                let args = {path: this.save_path, version: this.save_version};
                util.setOutput('trimmer_output', 'green', i18n.T('TrimmerLoadSuccess', args), 0);
                return Promise.resolve(this.save_path);
            }).bind(this);

            let error = (function (e) {
                let args = {path: this.save_path, error: e};
                util.setOutput('trimmer_output', 'red', i18n.T('TrimmerLoadFailed', args), 0);
                return Promise.resolve(e);
            }).bind(this);

            return p.then(load).catch(error);
        }
        return Promise.resolve(null);
    }

    listSave() {
        this.clearSelection();
        let s = document.getElementById('trimmer_save_selector');
        for (let i = s.options.length - 1; i > 0; i--) {
            s.remove(i);
        }

        let p = window.fetch('./list_save').then((r) => r.json());

        let readList = (function (saves) {
            for (let save of saves) {
                let o = document.createElement('option');
                o.value = save;
                o.text = save;
                s.appendChild(o);
                if (save == this.save_path) {
                    s.value = save;
                }
            }
            this.save_path = s.value;
            util.setOutput('trimmer_output', 'green', i18n.T('TrimmerListSuccess'), 0);
            return this.loadSave();
        }).bind(this);

        function error(e) {
            let info = i18n.T('TrimmerListFailed', {error: e});
            if (e.name == 'TypeError' && e.message == 'Failed to fetch') {
                info = i18n.T('TrimmerNotInServerMode');
            }
            util.setOutput('trimmer_output', 'red', info, 0);
            return Promise.resolve(e);
        }
        return p.then(readList).catch(error);
    }

    check() {
        let args = {blocks: Array.from(this.selected_blocks)};
        return confirm(i18n.E('TrimmerConfirm', args));
    }

    trim() {
        if (this.selected_blocks.size == 0) {
            util.setOutput('trimmer_output', 'red', i18n.T('TrimmerNotSelecting'), 0);
            return Promise.resolve(false);
        }
        if (!this.check()) {
            util.setOutput('trimmer_output', 'red', i18n.T('TrimmerCanceled'), 0);
            return Promise.resolve(false);
        }

        let cells = new Set();
        let blocks = [];

        for (let [ckey, value] of Object.entries(this.selected_cells)) {
            if (value == this.saved_cells[ckey]) {
                cells.add(ckey);
            }
        }
        for (let bkey of this.selected_blocks) {
            let ckey = bkey2ckey(bkey);
            if (!cells.has(ckey)) {
                blocks.push(bkey);
            }
        }

        let body = 'cells=' + Array.from(cells).join(';') + '&blocks=' + blocks.join(';');
        if (document.getElementById('trimmer_vehicles').checked) {
            body += '&vehicles=1';
        }
        if (document.getElementById('trimmer_animals').checked) {
            body += '&animals=1';
        }

        function ok(r) {
            util.setOutput('trimmer_output', 'green', i18n.T('TrimmerSuccess'), 0);
            return Promise.resolve(true);
        };

        function error(e) {
            util.setOutput('trimmer_output', 'red', i18n.T('TrimmerError', {error: e}), 0);
            return Promise.resolve(e);
        };
       
        let headers = {'Content-Type': 'application/x-www-form-urlencoded'};
        let p = window.fetch('./delete/' + this.save_path, {method: 'POST', body: body, headers: headers});
        return p.then(() => this.loadSave()).then(ok).catch(error);
    } 
};
