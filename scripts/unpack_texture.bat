pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python -m pzmap2dzi.texture -o "%out_path%\texture" -m 16 "%pz_path%"
popd

