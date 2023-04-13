pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\base" -t "%out_path%\texture" %common_param% %base_param% base "%map_path%"
popd
