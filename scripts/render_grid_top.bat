pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_grid_top.py -o "%out_path%\html\grid_top" -m 16 -v -c -S 1 "%map_path%"
popd
