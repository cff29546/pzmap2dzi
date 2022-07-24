pushd %~dp0..
python render_grid_top.py -o test_output\html\grid_top -m 16 -v -c -S 1 test_output\rosewood
popd
