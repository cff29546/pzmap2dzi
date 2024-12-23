pushd %~dp0
for /f "delims=" %%x in (python_version.txt) do set %%x
cd test_output
%python% ../../main.py render room objects
popd
pause