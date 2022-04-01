pushd %~dp0..
set /p out_path= <out_path.txt
set /p pz_path= <pz_path.txt
python -m pzmap2dzi.texture -o "%out_path%\texture" -m 16 "%pz_path%"
popd

