pushd %~dp0
for /f "delims=" %%x in (python_version.txt) do set %%x
%python% setup_test.py
%python% ../main.py copy
%python% ../main.py unpack
popd
pause