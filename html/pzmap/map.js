import { g } from "./globals.js";

export class Map {
    layers = 0;
    tiles = [];
    overlays = {};
    overlay_layer = 0;
    cell_rects = [];
    clip_list = [];
    info = {};
    available_types = [];

    constructor(root, map_type, name, base_map=null) {
        this.root = root;
        this.name = name;
        this.type = map_type;
        this.base_map = base_map;
        if (!this.base_map) {
            this.base_map = this;
        }
    }

    cell2pixel(cx, cy) {
        let x = this.x0;
        let y = this.y0;
        if (this.type == 'iso') {
            x += (cx - cy) * this.sqr * this.cell_size / 2;
            y += (cx + cy) * this.sqr * this.cell_size / 4;
        } else {
            x += cx * this.sqr * this.cell_size;
            y += cy * this.sqr * this.cell_size;
        }
        return {x: x, y: y};
    }

    getClipPoints(rects, remove=true) {
        let points = [];
        if (remove) {
            points.push({x: 0, y: 0});
            points.push({x: 0, y: this.h});
            points.push({x: this.w, y: this.h});
            points.push({x: this.w, y: 0});
        }
        points.push({x: 0, y: 0});
        for (let [x, y, w, h] of rects) {
            points.push(this.cell2pixel(x, y));
            points.push(this.cell2pixel(x + w, y));
            points.push(this.cell2pixel(x + w, y + h));
            points.push(this.cell2pixel(x, y + h));
            points.push(this.cell2pixel(x, y));
            points.push({x: 0, y: 0});
        }
        return points;
    }

    setClipByOtherMaps(maps, layer) {
        this.clip_list = [this.getClipPoints(this.cell_rects, false)];
        for (let i = maps.length - 1; i >= 0; i--) {
            let rlist = [];
            for (let r of maps[i].cell_rects) {
                for (let b of this.cell_rects) {
                    if (rectIntersect(b, r)) {
                        rlist.push(r);
                        break;
                    }
                }
            }
            if (rlist.length > 0) {
                this.clip_list.push(this.getClipPoints(rlist));
            }
        }
        
        for (let type of ['zombie', 'foraging']) {
            if (![undefined, 0, 'loading', 'delete'].includes(this.overlays[type])) {
                let clip_list = this.getClipList(this.info[type].scale, 0);
                this.overlays[type].setCroppingPolygons(clip_list);
            }
        }
        for (let type of ['room', 'objects']) {
            if (![undefined, 0, 'loading', 'delete'].includes(this.overlays[type])) {
                let clip_list = this.getClipList(this.info[type].scale, layer);
                this.overlays[type].setCroppingPolygons(clip_list);
            }
        }
    }

    getClipList(scale, layer) {
    let clip_list = [];
    let yshift = (this.type == 'top' ? 0 : 1.5 * this.base_map.sqr * layer);
    for (let clip of this.clip_list) {
        let points = [];
        for (let p of clip) {
            points.push({x: p.x / scale, y: (p.y - yshift) / scale})
        }
        clip_list.push(points);
    }
    return clip_list;
}

    getMapRoot() {
        return this.root;
        let prefix = 'maps/'+g.get['map_name']+'_';
			if (undefined == g.prefix){
				g.prefix = prefix;
			}
        if (this.base_map === this) {
            return prefix;
        }
        return prefix+'/mod_maps/' + this.name + '/'; 
    }

    getRelativePositionAndWidth(other_map) {
        let x = (this.x0 - other_map.x0) / this.scale;
        let y = (this.y0 - other_map.y0) / this.scale;
        let p = g.viewer.world.getItemAt(0).imageToViewportCoordinates(x, y);
        let width = other_map.w / this.w;
        return [p, width];
    }

    _load_tile(layer, opacity=1) {
        if (g.viewer) {
            let [p, width] = this.base_map.getRelativePositionAndWidth(this);
            if (layer < this.maxlayer && layer >= this.minlayer) {
                if (this.getTile(layer) == 0) {
                    this.setTile(layer, 'loading');
                    g.viewer.addTiledImage({
                        tileSource: this.root + 'base' + this.suffix + '/layer' + layer + '.dzi',
                        opacity: 1,
                        x: p.x,
                        y: p.y,
                        width: width,
                        success: (function (obj) {
                            if ([0, 'loading'].includes(this.getTile(layer))) {
                                this.setTile(layer, obj.item);
                                positionItem(obj.item, this.name, layer);
                                obj.item.setOpacity(opacity);
                            } else {
                                g.viewer.world.removeItem(obj.item);
                                if (this.getTile(layer) == 'delete') {
                                    this.setTile(layer, 0);
                                }
                            }
                        }).bind(this),
                        error: (function (e) {
                            if (['delete', 0, 'loading'].includes(this.getTile(layer))) {
                                this.setTile(layer, 0);
                            }
                        }).bind(this),
                    });
                } else {
                    if (!['delete', 'loading'].includes(this.getTile(layer))) {
                        this.getTile(layer).setOpacity(opacity);
                    }
                }
            }
        }
    }

    _load_overlay(type, layer) {
        if (g.viewer && layer < this.maxlayer && layer >= this.minlayer) {
            let [p, width] = this.base_map.getRelativePositionAndWidth(this);
            let shift = true;
            if (type == 'zombie' || type == 'foraging') {
                layer = 0;
                shift = false;
            }
            if (this.overlays[type] == 0) {
                this.overlays[type] = 'loading';
                g.viewer.addTiledImage({
                    tileSource: this.root + type + this.suffix + '/layer' + layer + '.dzi',
                    opacity: 1,
                    x: p.x,
                    y: p.y,
                    width: width,
                    success: (function (obj) {
                        if ([0, 'loading'].includes(this.overlays[type])) {
                            this.overlays[type] = obj.item;
                            if (shift) {
                                let clip_list = this.getClipList(this.info[type].scale, layer);
                                this.overlays[type].setCroppingPolygons(clip_list);
                            } else {
                                let clip_list = this.getClipList(this.info[type].scale, 0);
                                this.overlays[type].setCroppingPolygons(clip_list);
                            }
                        } else {
                            g.viewer.world.removeItem(obj.item);
                            if (this.overlays[type] == 'delete') {
                                this.overlays[type] = 0;
                            }
                        }
                    }).bind(this),
                    error: (function (e) {
                        if (['delete', 0, 'loading'].includes(this.overlays[type])) {
                            this.overlays[type] = 0;
                        }
                    }).bind(this),
                });
            }
        }
    }

    _unload_tile(layer) {
        if (layer < this.maxlayer && layer >= this.minlayer && this.getTile(layer) != 0) {
            if (['loading', 'delete'].includes(this.getTile(layer))) {
                this.setTile(layer, 'delete');
            } else {
                g.viewer.world.removeItem(this.getTile(layer));
                this.setTile(layer, 0);
            }
        }
        return
    }

    _unload_overlay(type) {
        if (this.overlays[type] != 0) {
            if (['loading', 'delete'].includes(this.overlays[type])) {
                this.overlays[type] = 'delete';
            } else {
                g.viewer.world.removeItem(this.overlays[type]);
                this.overlays[type] = 0;
            }
        }
    }

    setTile(layer, tile) {
        this.tiles[layer - this.minlayer] = tile;
    }

    getTile(layer) {
        return this.tiles[layer - this.minlayer];
    }

    setBaseLayer(layer) {
        let start = this.minlayer;
        if (layer >= 0) {
            start = 0;
        }
        for (let i = start; i < this.maxlayer ; i++) {
            if (i > layer) {
                if (i == layer + 1 && g.roof_opacity > 0) {
                    this._load_tile(i, g.roof_opacity / 100);
                } else {
                    this._unload_tile(i);
                }
            } else {
                this._load_tile(i);
            }
        }
        if (layer >= 0) {
            for (let i = this.minlayer; i < 0 ; i++) {
                this._unload_tile(i);
            }
        }
    }

    setOverlayLayer(overlay, layer) {
        for (let type of ['zombie', 'foraging', 'room', 'objects']) {
            if (overlay[type]) {
                if (!['zombie', 'foraging'].includes(type)) {
                    if (layer != this.overlay_layer) {
                        this._unload_overlay(type);
                    }
                }
                this._load_overlay(type, layer);
            } else {
                this._unload_overlay(type);
            }
        }
        this.overlay_layer = layer;
    }

    destroy() {
        this.setOverlayLayer({}, 0);
        for (let i = this.minlayer; i < this.maxlayer ; i++) {
            this._unload_tile(i);
        } 
    }

    getLayerRange() {
        let i = -1, j = 0;
        let root = this.root;
        let suffix = this.suffix;
        function getmax(r) {
            if (r.ok) {
                i += 1;
                return window.fetch(root + 'base' + suffix + '/layer' + i + '.dzi').then(getmax, getmax);
            } else {
                return Promise.resolve(i);
            }
        };
        function getmin(r) {
            if (r.ok) {
                j -= 1;
                return window.fetch(root + 'base' + suffix + '/layer' + j + '.dzi').then(getmin, getmin);
            } else {
                return Promise.resolve(j+1);
            }
        };

        let setrange = (function (r) {
            [this.minlayer, this.maxlayer] = r;
            return Promise.resolve(r);
        }).bind(this)
 
        return Promise.all([getmin({ok: 1}), getmax({ok: 1})]).then(setrange);
    }

    typeToSuffix(type) {
        return (type == 'top') ? '_top' : '';
    }

    isTypeAvailable(type) {
        let suffix = this.typeToSuffix(type);
        return window.fetch(this.root + 'base' + suffix + '/map_info.json')
            .then((r) => r.json())
            .then((j) => Promise.resolve(type))
            .catch((e) => Promise.resolve(null));
    }

    availableTypes() {
        let t = [];
        for (let type of ['iso', 'top']) {
            t.push(this.isTypeAvailable(type));
        }
        return Promise.all(t).then((r) => {
            let types = [];
            for (let type of r) {
                if (type) {
                    types.push(type);
                }
            }
            this.available_types = types;
            return Promise.resolve(types);
        });
    }

    init() {
        return this.availableTypes().then((types) => {
            if (!this.type) {
                if (types.length) {
                    this.type = types[0];
                } else {
                    this.type = 'iso';
                }
            }
            return this.initMap();
        });
    }

    initMap() {
        let root = this.root;
        this.suffix = this.typeToSuffix(this.type);
        let suffix = this.suffix;
        let empty = function(e) { return Promise.resolve({})};
        function getinfo(type) {
            return window.fetch(root + type + suffix + '/map_info.json')
                .then((r) => r.json()).catch((e) => Promise.resolve({}));
        }

        let setlayer = (function (r) {
            this.minlayer = this.minlayer > 0 ? 0: this.minlayer;
            this.maxlayer = this.maxlayer < 1 ? 1: this.maxlayer;
            this.layers = this.maxlayer - this.minlayer;
            this.tiles = Array(this.layers).fill(0);
            return Promise.resolve(this);
        }).bind(this);

        let infos = ['base', 'zombie', 'foraging', 'room', 'objects'];
        if (this.type == 'top') {
            infos = ['base', 'zombie', 'foraging'];
        }
        let setinfo = (function (r) {
            for (let i in infos) {
                let type = infos[i];
                this.info[type] = r[i];
                this.info[type].scale = 1;
                if ('skip' in r[i]) {
                    this.info[type].scale <<= r[i].skip;
                }
                if (type !== 'base') {
                    this.overlays[type] = 0;
                }
            }

            if (this.info.base.pz_version) {
                this.w = this.info.base.w * this.info.base.scale;
                this.h = this.info.base.h * this.info.base.scale;
                this.scale = this.info.base.scale;
                this.x0 = this.info.base.x0;
                this.y0 = this.info.base.y0;
                this.sqr = this.info.base.sqr;
                this.cell_rects = this.info.base.cell_rects;
                this.cell_size = this.info.base.cell_size;
                this.block_size = this.info.base.block_size;
                this.cell_in_block = this.cell_size / this.block_size;
                this.pz_version = this.info.base.pz_version;
                this.render_version = this.info.base.pzmap2dzi_version;
                this.branch = this.info.base.git_branch;
                this.commit = this.info.base.git_commit;
                this.minlayer = this.info.base.minlayer;
                this.maxlayer = this.info.base.maxlayer;
            }

            if (this.minlayer === undefined || this.maxlayer === undefined) {
                return this.getLayerRange();
            } else {
                return Promise.resolve([this.minlayer, this.maxlayer]);
            }
        }).bind(this);

        let ptypes = [];
        for (let type of infos) {
            ptypes.push(getinfo(type));
        }
        return Promise.all(ptypes).then(setinfo).then(setlayer);
    }
};

// order layered maps
function positionItem(item, name, layer) {
    let pos = 1;
    for (let i = g.minLayer; i < g.maxLayer; i++) {
        if (name == '' && layer == i) {
            g.viewer.world.setItemIndex(item, pos);
            return;
        }
        if (![undefined, 0, 'loading', 'delete'].includes(g.base_map.getTile(i))) {
            pos++;
        }
        for (let j = 0; j < g.mod_maps.length; j++ ) {
            if (name == g.mod_maps[j].name && layer == i) {
                g.viewer.world.setItemIndex(item, pos);
                return;
            }
            if (![undefined, 0, 'loading', 'delete'].includes(g.mod_maps[j].getTile(i))) {
                pos++;
            }
        }
    }
}

function positionAll() {
    let pos = 1;
    for (let i = g.minLayer; i < g.maxLayer; i++) {
        if (![undefined, 0, 'loading', 'delete'].includes(g.base_map.getTile(i))) {
            g.viewer.world.setItemIndex(g.base_map.getTile(i), pos);
            pos++;
        }
        for (let j = 0; j < g.mod_maps.length; j++ ) {
            if (![undefined, 0, 'loading', 'delete'].includes(g.mod_maps[j].getTile(i))) {
                g.viewer.world.setItemIndex(g.mod_maps[j].getTile(i), pos);
                pos++;
            }
        }
    }
}

function rectIntersect(r1, r2) {
    let [x1, y1, w1, h1] = r1;
    let [x2, y2, w2, h2] = r2;
    return (x1 < x2 + w2) && (x2 < x1 + w1) && (y1 < y2 + h2) && (y2 < y1 + h1);
}
