pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x
for /f "delims=" %%x in (%~dp0config_update.txt) do set %%x

mkdir test_output\rosewood
copy /Y "%pz_path%\media\maps\Muldraugh, KY\27_38.lotheader" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\world_27_38.lotpack" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\27_39.lotheader" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\world_27_39.lotpack" test_output\rosewood\
copy /Y "%pz_path%\media\maps\Muldraugh, KY\objects.lua" test_output\rosewood\
xcopy /Q /E /I /Y html test_output\html
popd