pushd %~dp0..
set /p pz_path= <pz_path.txt
mkdir test_output\rosewood
copy /Y "%pz_path%\media\maps\Muldraugh, KY\27_38.lotheader" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\world_27_38.lotpack" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\27_39.lotheader" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\world_27_39.lotpack" test_output\rosewood\
xcopy /Q /E /I /Y html test_output\html
popd