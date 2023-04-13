pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\zombie" %common_param% %zombie_param% zombie "%map_path%"
popd
