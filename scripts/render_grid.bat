pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\grid" %common_param% %grid_param% grid "%map_path%"
popd