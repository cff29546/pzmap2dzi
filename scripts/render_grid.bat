pushd %~dp0..
set /p pz_path= <pz_path.txt
set /p out_path= <out_path.txt
python render_grid.py -o "%out_path%\html\grid" -m 16 -v --cell-grid --block-grid --group-size 100 "%pz_path%\media\maps\Muldraugh, KY"
popd