pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\base_top" -t "%out_path%\texture" %common_param% %common_top_param% %base_top_param% base_top "%map_path%"
popd
