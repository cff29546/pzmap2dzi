pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_zombie_top.py -o "%out_path%\html\zombie_top" -m 16 -v -S 1 "%map_path%"
popd
