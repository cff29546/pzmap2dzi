pushd %~dp0..
python render_foraging_top.py -o test_output\html\foraging_top -m 16 -v -S 1 test_output\rosewood
popd
