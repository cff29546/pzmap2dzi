# Change log

# 2025-05-23: 1.0.9 + UI 1.0.11

* marker system and dynamic ui refactor
* added square cursor

# 2025-05-20: 1.0.9 + UI 1.0.10

* load overlays on start by params in the query string
  * example: `pzmap.html?overlays=zombie,foraging,room,objects`

# 2025-03-19: 1.0.8 + UI 1.0.9

* Align tiles to map origin

# 2025-03-19: 1.0.6 + UI 1.0.9

* Fix coordinates offset
* Copy coordinates to clipboard by pressing 'c'

# 2025-03-19: 1.0.6 + UI 1.0.8

* Fix recent change to 'getSquare' function break Marker and Trimmer drag events
* Optimize performance of 'i18n.update' function
* Use named function for 'onMouseMove' to prevent duplication of anonymous listeners

# 2025-03-18: 1.0.6 + UI 1.0.7

* When only top view data exists, open as top view
* Fix top view blurry by turn off OSD image smoothing

# 2025-03-16: 1.0.6 + UI 1.0.6

* Fix top view overlay rects render
* Add pointer coordinates

# 2025-03-14: 1.0.5 + UI 1.0.5

* Rename the 'copy' command to 'deploy'
* Add link to commit on UI

# 2025-03-08: 1.0.4 + UI 1.0.4

* Support B42.4 foraging zones
* Customizable colors for foraging and objects

# 2025-02-12: 1.0.3 + UI 1.0.2

* B42 support
* .pzby basement file parser
