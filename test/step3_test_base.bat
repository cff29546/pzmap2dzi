pushd %~dp0..
python render_base.py -o test_output\html\base -t test_output\texture -m 16 -v --group-size 100 -s "<f9>" test_output\rosewood
popd