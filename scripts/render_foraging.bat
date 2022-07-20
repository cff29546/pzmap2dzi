pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_foraging.py -o "%out_path%\html\foraging" -m 16 -v --group-size 100 "%pz_path%\media\maps\%map_name%"
popd
