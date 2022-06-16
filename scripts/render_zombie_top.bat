pushd %~dp0..
set /p pz_path= <pz_path.txt
set /p out_path= <out_path.txt
python render_zombie_top.py -o "%out_path%\html\zombie_top" -m 16 -v -s 1 "%pz_path%\media\maps\Muldraugh, KY"
popd
