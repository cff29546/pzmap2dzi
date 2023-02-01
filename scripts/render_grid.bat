pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_grid.py -o "%out_path%\html\grid" -m 16 -v --cell-grid --block-grid --group-size 100 "%map_path%"
popd