pushd %~dp0..
python render_zombie_top.py -o test_output\html\zombie_top -m 16 -v -s 1 test_output\rosewood
popd
