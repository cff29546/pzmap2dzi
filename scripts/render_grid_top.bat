pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\grid_top" %common_param% %common_top_param% %grid_top_param% grid_top "%map_path%"
popd
