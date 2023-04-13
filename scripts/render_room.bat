pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\room" %common_param% %room_param% room "%map_path%"
popd