import { g } from "./globals.js";
import * as util from "./util.js";
import * as i18n from "./i18n.js";

var LEGEND_TEMPLATE = {
    foraging: '<div class="legend" style="background-color:{color}"></div><span id="{id}"></span>',
    objects: '<div class="legend" style="border-color:{color}; border-width: 3px;"></div><span id="{id}"></span>'
};

function genLegendsUI(type, mapping) {
    const label_id = type + '_legends_text';
    const ids = [label_id];
    let html = '<b id="' + label_id + '"></b>';

    const template = LEGEND_TEMPLATE[type];
    if (template) {
        for (const key in mapping) {
            const color = mapping[key];
            if (color == 'skip') {
                continue;
            }
            const legend_id = type + '_legend_' + key;
            html += util.format(template, {color: color, id: legend_id});
            ids.push(legend_id);
        }
    }
    return [ids, html];
}

var MAP_HTML = `
<button id="map_all_btn" onclick="toggleAllMaps()"></button>
<select id="map_selector" onchange="onMapSelect()">
    <option id="map_selector_dummy_option" value=""></option>
</select>
<b id="map_loaded_text"></b>
<div id="map_list" style="display: inline-block"></div>
<div id="map_output" style="display: inline-block"></div>`;

var MAP_IDS = [
    'map_all_btn',
    'map_selector_dummy_option',
    'map_loaded_text'
];

var MARKER_HTML = `
<div style="display: flex">
<div style="display: inline-block">
    <table style="white-space: nowrap; text-align: right">
    <tr>
        <td><button id="marker_save_btn" type="button" style="width: 100%" onclick="onMarkerSave()">Save</button></td>
        <td id="marker_x_text">x:</td>
        <td><input id="marker_x" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td id="marker_y_text">y:</td>
        <td><input id="marker_y" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td id="marker_layer_text">layer:</td>
        <td><input id="marker_layer" type="number" step="1" style="width: 3em" onchange="onMarkerInput(this)" /></td>
        <td style="display: flex;">
            <span id="marker_name_text">name:</span> <input id="marker_name" type="text" style="flex: 1;" onchange="onMarkerInput(this)"/>
        </td>
        <td id="marker_description_text">description:</td>
    </tr>
    <tr>
        <td><button id="marker_delete_btn" type="button" onclick="onMarkerDelete(event)" style="width: 100%">Delete</button></td>
        <td id="marker_width_text">width:</td>
        <td><input id="marker_width" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td id="marker_height_text">height:</td>
        <td><input id="marker_height" type="number" step="1" style="width: 5em" onchange="onMarkerInput(this)"/></td>
        <td id="marker_visibility_text">visibility:</td>
        <td>
            <select id="marker_visiable_zoom_level" onchange="onMarkerInput(this)">
                <option id="marker_visiable_zoom_level_0" value="0">always</option>
                <option id="marker_visiable_zoom_level_1" value="1">mid zoom</option>
                <option id="marker_visiable_zoom_level_2" value="2">close zoom</option>
            </select>
        </td>
        <td class="text-right">
            <button id="marker_import_btn" type="button" onclick="onMarkerImport()">Import</button>
            <button id="marker_export_btn" type="button" onclick="onMarkerExport()">Export</button>
            <button id="marker_default_btn" type="button" onclick="onMarkerDefault()">Load Default</button>
            <button id="marker_clear_btn" type="button" onclick="onMarkerClear()">Remove All</button>
        </td>
        <td><a id="marker_help_btn" href="" onclick="return toggleMarkerHelp();">Show Help</a></td>
    </tr>
    </table>
</div>
<div style="display: inline-block; width: 100%">
<table style="width: 100%"><td>
    <textarea id="marker_desc" rows="2" style="width: 100%; resize: none;" onchange="onMarkerInput(this)"></textarea>
</td></table>
</div>
</div>
<div style="display: flex;">
<button id="marker_focus_btn" type="button" onclick="onMarkerFocus()" title="focus">&#x1f3af;</button>
<button id="marker_deselect_btn" type="button" onclick="onMarkerDeselect()">Deselect(Esc)</button>
<input type="checkbox" id="marker_point" checked onchange="togglePointMark(this)">
<label id="marker_point_label" for="marker_point">Show Point</label>
<input type="checkbox" id="marker_area" checked onchange="toggleAreaMark(this)">
<label id="marker_area_label" for="marker_area">Show Area</label>
<input type="checkbox" id="marker_name" checked onchange="toggleMarkName(this)">
<label id="marker_name_label" for="marker_name">Show Name</label>
<div class="legend point" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_current">marks on this floor</span>
<div class="legend point above" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_above">marks above</span>
<div class="legend point below" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_below">marks below</span>
<div class="legend point selected" style="width: 1em; height: 1em; visibility: visible;"></div><span id="mark_selected">the selected mark</span>
<span id="marker_output" class="inline" style="flex: 1; background-color: white; margin-left: 1em;"></span>
</div>
<div id="marker_help"></div>`;

var MARKER_IDS = [
    "marker_save_btn", "marker_x_text", "marker_y_text", "marker_layer_text",
    "marker_name_text", "marker_description_text",

    "marker_delete_btn", "marker_width_text", "marker_height_text", "marker_visibility_text", 
    "marker_visiable_zoom_level_0", "marker_visiable_zoom_level_1", "marker_visiable_zoom_level_2",
    "marker_import_btn", "marker_export_btn", "marker_default_btn", "marker_clear_btn", 'marker_help_btn',

    "marker_focus_btn", "marker_deselect_btn", "marker_point_label", "marker_area_label",
    "marker_name_label", "mark_current", "mark_above", "mark_below", "mark_selected"];

var MARKER_HELP_HTML = '<div id="marker_help_text"></div>';
var MARKER_HELP_IDS = ['marker_help_btn', 'marker_help_text'];

var TRIMMER_HTML = `
<b id="trimmer_title"></b> <span id="trimmer_legends_text"></span>
<div class="legend" style="background-color:#0f0"></div><span id="trimmer_saved"></span>
<div class="legend" style="background-color:#00f"></div><span id="trimmer_partial_saved"></span>
<div class="legend" style="background-color:#f00"></div><span id="trimmer_selected"></span>
<div class="legend" style="background-color:#ff0"></div><span id="trimmer_partial_selected"></span>
<a id="trimmer_help_btn" href="" class="text-right" onclick="return toggleTrimmerHelp();"></a>
<div>
<select id="trimmer_save_selector" onchange="onTrimmerSaveSelect()">
    <option id="trimmer_save_selector_dummy_option" value=""></option>
</select>
<button id="trimmer_refresh_btn" type="button" onclick="onTrimmerRefresh()"></button>
<input type="checkbox" id="trimmer_vehicles" checked>
<label id="trimmer_vehicles_label" for="trimmer_vehicles"></label>
<input type="checkbox" id="trimmer_animals">
<label id="trimmer_animals_label" for="trimmer_animals"></label>
<button id="trimmer_trim_btn" onclick="onTrim()"></button>
<div id="trimmer_output" style="display: inline-block"></div>
<button id="trimmer_browse_btn" class="text-right" onclick="onTrimmerBrowse()"></button>
</div>
<div id="trimmer_help"></div>`;

var TRIMMER_IDS = [
    "trimmer_title", "trimmer_legends_text", "trimmer_saved", "trimmer_partial_saved",
    "trimmer_selected", "trimmer_partial_selected", "trimmer_help_btn",
    "trimmer_save_selector_dummy_option", "trimmer_refresh_btn", "trimmer_vehicles_label",
    "trimmer_animals_label", "trimmer_trim_btn", "trimmer_browse_btn"];

var TRIMMER_HELP_HTML = '<div id="trimmer_help_text"></div>';
var TRIMMER_HELP_IDS = ['trimmer_help_btn', 'trimmer_help_text'];

export function createUI() {
    const ui = {};
    ui.map = {html: MAP_HTML, ids: MAP_IDS};
    ui.marker = {html: MARKER_HTML, ids: MARKER_IDS};
    ui.marker_help = {html: MARKER_HELP_HTML, ids: MARKER_HELP_IDS};
    ui.trimmer = {html: TRIMMER_HTML, ids: TRIMMER_IDS};
    ui.trimmer_help = {html: TRIMMER_HELP_HTML, ids: TRIMMER_HELP_IDS};

    let legends = util.getByPath(g, 'base_map', 'info', 'foraging', 'legends');
    if (!legends) {
        legends = {
            Nav: 'White',
            TownZone: 'Blue',
            TrailerPark: 'Cyan',
            Vegitation: 'Yellow',
            Forest: 'Lime',
            DeepForest: 'Green',
            FarmLand: 'Magenta',
            Farm: 'Red'
        }
    }
    ui.foraging = {};
    [ui.foraging.ids, ui.foraging.html] = genLegendsUI('foraging', legends);
    ui.foraging.html += `<span>&emsp; &emsp;</span>`;

    legends = util.getByPath(g, 'base_map', 'info', 'objects', 'legends');
    if (!legends) {
        legends = {ZombiesType: 'Red', ParkingStall: 'Blue', ZoneStory: 'Yellow'}
    }
    ui.objects = {};
    [ui.objects.ids, ui.objects.html] = genLegendsUI('objects', legends);

    return ui;
}

export function genAboutUI() {
    const div_begin = '<div style="display: inline-block; float: right; background-color: Yellow; text-align: left;">';
    const div_end = '</div>';
    const args = {
        pzmap2dzi: '<a id="pzmap2dzi" href="https://github.com/cff29546/pzmap2dzi" target="_blank">pzmap2dzi</a>',
        osd: '<a id="osd" href="https://github.com/openseadragon/openseadragon" target="_blank">OpenSeaDragon</a>',
        pzwiki: '<a id="pzwiki" href="https://pzwiki.net/wiki/Project_Zomboid_Wiki" target="_blank">PZwiki</a>',
        pz: '<a id="pz" href="https://projectzomboid.com" target="_black">Project Zomboid</a>',
        pz_steam: '<a id="pz_steam" href="https://store.steampowered.com/app/108600/Project_Zomboid" target="_black">Project Zomboid</a>',
        pz_version: util.getByPath(g, 'base_map', 'pz_version')
    };

    const link_template = '<a href="https://github.com/cff29546/pzmap2dzi/tree/{commit}" title="{branch}" target="_blank">{version}</a>';
    if (g.base_map.commit) {
        args.render_version = util.format(link_template, {
            commit: g.base_map.commit,
            branch: g.base_map.branch,
            version: g.base_map.render_version
        });
    } else {
        args.render_version = g.base_map.render_version;
    }
    if (g.conf.git_commit) {
        args.ui_version = util.format(link_template, {
            commit: g.conf.git_commit,
            branch: g.conf.git_branch,
            version: g.conf.version
        });
    } else {
        args.ui_version = g.conf.version;
    }
    const html = div_begin + i18n.T('About', args) + div_end;
    const ids = ['pzmap2dzi', 'osd', 'pzwiki', 'pz', 'pz_steam'];
    return [ids, html];
}

export function getMarkerUIData() {
    const data = {
        x: 0,
        y: 0,
        layer: g.currentLayer,
        width: 0,
        height: 0,
    };
    const missing = {};
    for (const key of Object.keys(data)) {
        const value = Number.parseInt(util.getValue('marker_' + key));
        if (!Number.isInteger(value)) {
            util.setValue('marker_' + key, '');
            missing[key] = true;
        } else {
            data[key] = value;
        }
    }
    data.visiable_zoom_level = Number(util.getValue('marker_visiable_zoom_level'));
    if (!Number.isInteger(data.visiable_zoom_level) || data.visiable_zoom_level < 0 || data.visiable_zoom_level > 2) {
        util.setValue('marker_visiable_zoom_level', 0);
        data.visiable_zoom_level = 0;
    }

    data.missing = missing;
    data.rects = [{
        x: data.x,
        y: data.y,
        width: data.width,
        height: data.height
    }];

    if (data.layer >= g.maxLayer) {
        data.layer = g.maxLayer - 1;
        util.setValue('marker_layer', data.layer);
    }

    if (data.layer < g.minLayer) {
        data.layer = g.minLayer;
        util.setValue('marker_layer', data.layer);
    }
    for (const key of ['name', 'desc']) {
        data[key] = util.getValue('marker_' + key);
    }
    return data;
}

export function setMarkerUIData(data) {
    const int_keys = ['x', 'y', 'width', 'height', 'layer'];
    const text_keys = ['name', 'desc'];
    let obj = {};
    if (data.type == 'area') {
        if (data.rects.length > 0) {
            let idx = data.selected_index;
            if (idx < 0 && data.rects.length == 1) {
                idx = 0;
            }
            if (idx >= 0 && idx < data.rects.length) {
                obj = data.rects[idx];
            }
        }
    }
    for (const key of int_keys) {
        let value = obj[key];
        if (value === undefined) {
            value = data[key];
        }
        value = Number(value);
        if (!Number.isInteger(value)) {
            value = '';
        }
        util.setValue('marker_' + key, value);
    }
    for (const key of text_keys) {
        util.setValue('marker_' + key, data[key] || '');
    }
    let zoom_level = Number(data.visiable_zoom_level);
    if (!Number.isInteger(zoom_level) || zoom_level < 0 || zoom_level > 2) {
        zoom_level = 0;
    }
    util.setValue('marker_visiable_zoom_level', zoom_level);

}