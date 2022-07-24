pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

python check_missing_textures.py -t "%out_path%\texture" -v "%pz_path%\media\maps\%map_name%"
popd
