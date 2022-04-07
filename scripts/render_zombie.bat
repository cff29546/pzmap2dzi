pushd %~dp0..
set /p pz_path= <pz_path.txt
set /p out_path= <out_path.txt
python render_zombie.py -o "%out_path%\html\zombie" -m 16 -z -v --group-size 100 "%pz_path%\media\maps\Muldraugh, KY"
popd
