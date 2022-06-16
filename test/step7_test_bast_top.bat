pushd %~dp0..
python render_base_top.py -o test_output\html\base_top -t test_output\texture -m 16 -v --layer0-fmt jpg -r avg -s 1 test_output\rosewood
popd
