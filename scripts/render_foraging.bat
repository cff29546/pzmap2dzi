pushd %~dp0..
set /p pz_path= <pz_path.txt
set /p out_path= <out_path.txt
python render_foraging.py -o "%out_path%\html\foraging" -m 16 -v --group-size 100 "%pz_path%\media\maps\Muldraugh, KY"
popd
