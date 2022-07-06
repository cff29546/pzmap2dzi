pushd %~dp0..
python render_objects.py -o test_output\html\objects -m 16 -v --group-size 100 -s "<f9>" test_output\rosewood
popd