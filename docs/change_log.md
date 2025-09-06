# Change log

# 2025-09-07: 1.1.5 + UI 1.1.5

* Add texture location script

# 2025-09-06: 1.1.4 + UI 1.1.5

* Add coordinates overlay system

# 2025-09-06: 1.1.4 + UI 1.1.4

* Render marks with svg
* Dynamic streets overlay

# 2025-08-26: 1.1.3 + UI 1.1.3

* Avoid redundant texture unpacking when files are already present

# 2025-08-24: 1.1.2 + UI 1.1.3

* Enable resizing of area marks
* Render rooms and objects as area marks
* Overlay rooms and objects dynamically in viewer

# 2025-08-19: 1.1.1 + UI 1.1.2

* Fix R-tree index deletion resulting illegal tree
* Mark editor refactor
* Add support of diff-sum area mark
* Node debug mode R-tree index

# 2025-08-15: 1.1.1 + UI 1.1.1

* Better multi-rect area rendering
* R-tree accelerated visible range mark rendering

# 2025-06-12: 1.0.9 + UI 1.0.12

* Add support of multi-rect area marks

# 2025-05-23: 1.0.9 + UI 1.0.11

* Marker system and dynamic ui refactor
* Added square cursor

# 2025-05-20: 1.0.9 + UI 1.0.10

* Load overlays on start by params in the query string
  * Example: `pzmap.html?overlays=zombie,foraging,room,objects`

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
