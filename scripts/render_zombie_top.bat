pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\zombie_top" %common_param% %common_top_param% %zombie_top_param% zombie_top "%map_path%"
popd
