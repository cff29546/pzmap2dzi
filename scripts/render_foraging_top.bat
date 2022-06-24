pushd %~dp0..
set /p pz_path= <pz_path.txt
set /p out_path= <out_path.txt
python render_foraging_top.py -o "%out_path%\html\foraging_top" -m 16 -v -S 1 "%pz_path%\media\maps\Muldraugh, KY"
popd
