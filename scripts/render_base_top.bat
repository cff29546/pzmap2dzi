pushd %~dp0..
set /p out_path= <out_path.txt
set /p pz_path= <pz_path.txt
python render_base_top.py -o "%out_path%\html\base_top" -t "%out_path%\texture" -m 16 -v --layer0-fmt png -r avg -S 1 "%pz_path%\media\maps\Muldraugh, KY"
popd
