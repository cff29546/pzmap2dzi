pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\objects" %common_param% %objects_param% objects "%map_path%"
popd