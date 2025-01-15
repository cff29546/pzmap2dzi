Based on OpenSeadragon 5.0.1, the following functions behavior have been modified to meet pzmap2dzi requirement.
- Drawer._clipWithPolygons
- TiledImage.setCroppingPolygons

* Diff details
```
--- openseadragon.js
+++ openseadragon-modify.js
@@ -20489,14 +20489,14 @@
      */
     _clipWithPolygons (polygons, useSketch) {
         var context = this._getContext(useSketch);
-        context.beginPath();
         for(const polygon of polygons){
+            context.beginPath();
             for(const [i, coord] of polygon.entries() ){
                 context[i === 0 ? 'moveTo' : 'lineTo'](coord.x, coord.y);
             }
+            context.clip();
         }

-        context.clip();
     }

     /**

```