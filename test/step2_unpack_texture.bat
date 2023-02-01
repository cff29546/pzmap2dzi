pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x
for /f "delims=" %%x in (%~dp0config_update.txt) do set %%x

python -m pzmap2dzi.texture -o test_output\texture -m 16 -z "%pz_path%" %additional_texture_packs%
popd

