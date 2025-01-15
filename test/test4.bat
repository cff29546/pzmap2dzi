pushd %~dp0
for /f "delims=" %%x in (env.txt) do set %%x
cd test_output
%python% ../../main.py render foraging foraging_top
popd
pause