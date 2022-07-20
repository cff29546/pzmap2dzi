pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_base.py -o "%out_path%\html\base" -t "%out_path%\texture" -m 16 -v --layer0-fmt jpg --group-size 100 "%pz_path%\media\maps\%map_name%"
popd
