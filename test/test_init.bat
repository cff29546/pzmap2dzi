pushd %~dp0
for /f "delims=" %%x in (env.txt) do set %%x
%python% setup_test.py
cd test_output
%python% ../../main.py copy
%python% ../../main.py unpack
popd
pause
