pushd %~dp0
for /f "delims=" %%x in (env.txt) do set %%x
set case=%1
if "%case%"=="" set case=case_default.yaml
%python% setup_test.py %case%
cd test_output
%python% ../../main.py copy
%python% ../../main.py unpack
popd
pause
