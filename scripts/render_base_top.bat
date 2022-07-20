pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_base_top.py -o "%out_path%\html\base_top" -t "%out_path%\texture" -m 16 -v --layer0-fmt png -r avg -S 1 "%pz_path%\media\maps\%map_name%"
popd
