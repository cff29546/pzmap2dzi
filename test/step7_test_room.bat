pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x
for /f "delims=" %%x in (%~dp0config_update.txt) do set %%x

%python% main.py -o test_output\html\room %common_param% %room_param% room test_output\rosewood
popd