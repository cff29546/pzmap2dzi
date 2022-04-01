pushd %~dp0..
python render_grid.py -o test_output\html\grid -m 16 -v --cell-grid --block-grid --group-size 100 -s "<f9>" test_output\rosewood
popd