export var g = {
    defaults: {
			get: {
				'map_name': '' // no default map_name for offline viewing
			}
		},
    map_type: 'iso',
    overlays: {},
    mapui: 0,
    gridui: 0,
    trimmerui: 0,
    markerui: 0,
    aboutui: 0,
    currentLayer: 0,
		get: {}
};
function populateGet() {
  var obj = {}, params = location.search.slice(1).split('&');
  for(var i=0,len=params.length;i<len;i++) {
    var keyVal = params[i].split('=');
    obj[decodeURIComponent(keyVal[0])] = decodeURIComponent(keyVal[1]);
  }
  return obj;
}
export function initGlobals() {
    g.viewer = 0;
    g.base_map = 0;
    g.mod_maps = [];
    g.roof_opacity = 0;
    g.minLayer = 0;
    g.maxLayer = 0;
    g.grid = 0;
		g.get = populateGet();
    if (undefined == g.get['map_name']){
			g.get['map_name'] = g.defaults['map_name'];
		}
};
