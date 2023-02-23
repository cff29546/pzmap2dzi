pushd %~dp0..
python render_zombie.py -o test_output\html\zombie -m 16 -z -v --group-level 2 -s "<f9>" test_output\rosewood
popd
