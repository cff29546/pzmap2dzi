pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

%python% main.py -o "%out_path%\html\foraging" %common_param% %foraging_param% foraging "%map_path%"
popd
