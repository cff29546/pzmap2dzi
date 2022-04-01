pushd %~dp0..
set /p out_path= <out_path.txt
set /p pz_path= <pz_path.txt
python render_base.py -o "%out_path%\html\base" -t "%out_path%\texture" -m 16 -v --group-size 100 "%pz_path%\media\maps\Muldraugh, KY"
popd