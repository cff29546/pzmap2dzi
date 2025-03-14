pushd %~dp0
for /f "delims=" %%x in (env.txt) do set %%x
set case=%1
if "%case%"=="" set case=case_default.yaml
%python% setup_test.py -o %output% %case%
cd /d %output%
%python% %~dp0..\main.py deploy
%python% %~dp0..\main.py unpack
popd
pause
