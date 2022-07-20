pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_room.py -o "%out_path%\html\room" -m 16 -v --group-size 100 "%pz_path%\media\maps\%map_name%"
popd