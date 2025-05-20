# Web Viewer User Manual

## Start the web viewer

1. Enter the `html` folder under the output path. It should have the following structure:
```
html
├── map_data/
├── openseadragon/
├── pzmap/
├─ chrome.bat
├─ chrome_allow_file(need close chrome first).bat
├─ chrome_no_sicurity.bat
├─ pzmap.html
├─ pzmap.js
├─ pzmap_config.json
├─ run_server.bat
├─ server.py
└─ server_config.txt
```

2. Bypass Cross-Origin Resource Sharing Policies (CORS) and start the viewer

    Directly open `pzmap.html` will NOT work, as CORS will refuse to load Deep Zoom tiles from your locale disk by default.

    There are 3 ways to bypass CORS:

    1. Option 1: Start a server and host your files on your drive
        - Run `run_server.bat`
        - Afterwards, you can open `http://localhost:8880/pzmap.html` to access the viewer
    2. Option 2: Disable Chrome security feature
        - Run `chrome_no_sicurity.bat` to open `pzmap.html` with security disabled.
    3. Option 3: Restart Chrome to allow locale file access
        - Close Chrome (all tabs) first
        - Then run `chrome_allow_file(need close chrome first).bat`

## Using Web viewer
- Switching floors
    - Option 1: Use the selection box on top left
    - Option 2: Use hotkey `Shift+MouseWheelUp` and `Shift+MouseWheelDown` to go up and down floors.
- Mod maps overlay, 
    - Use the `Mod Map` button to toggle the UI
    ![Overlay Map Example](./img/overlay_map.png)

- Info Overlay
    - Use the `Zombie`, `Foraging`, `Grid`, `Room`, or `Objects` buttons to enable/disable overlay
    - (The overlay of `grid`, `room`, and `objects` will reflect the currently selected floor)
    ![Zombie Heatmap Example](./img/zombie.jpg)
    ![Foraging zones Example](./img/foraging.jpg)
    ![Grid Example](./img/grid.gif)
    ![Room Example](./img/room.jpg)

- Switching between isometric view and top view
    - Use the `Switch to xxx View` button (it is only available when both isometric and top view output data exists)

- Use Save File Trimmer
    1. Edit `server_config.txt` and set the `save_path` variable to your save folder before starting the server (The default value is set for Windows 10)
    2. The viewer must start in server mode using `run_server.bat`
    ![Save File Trimmer Example](./img/trimmer.gif)

- Marking system, 
    - Use the `Marker` button to toggle the UI
    - Then, use the `Load Default` button for the default marker

## Hotkeys

`Shift+MouseWheelUp/MouseWheelDown`: go up/down floors

`Esc`: Delete selection in Marker UI

`c`: Copy cursor coordinates

