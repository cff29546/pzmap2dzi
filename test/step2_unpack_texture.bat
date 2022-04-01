pushd %~dp0..
set /p pz_path= <pz_path.txt
python -m pzmap2dzi.texture -o test_output\texture -m 16 "%pz_path%"
popd

