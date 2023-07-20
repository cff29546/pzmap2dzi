pushd %~dp0
for /f "delims=" %%x in (python_version.txt) do set %%x
%python% ../main.py render base base_top
popd
pause