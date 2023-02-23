pushd %~dp0..
python render_room.py -o test_output\html\room -m 16 -v --group-level 2 -s "<f9>" test_output\rosewood
popd