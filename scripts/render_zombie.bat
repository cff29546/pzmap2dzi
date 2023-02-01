pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python render_zombie.py -o "%out_path%\html\zombie" -m 16 -z -v --group-size 100 "%map_path%"
popd
