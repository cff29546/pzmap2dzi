pushd %~dp0..
python render_room.py -o test_output\html\room -m 16 -v --group-size 100 -s "<f9>" test_output\rosewood
popd