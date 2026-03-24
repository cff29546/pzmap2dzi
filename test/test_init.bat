@echo off
pushd %~dp0
for /f "delims=" %%x in (env.txt) do set %%x
set case=%1
if "%case%"=="" set case=case_default.yaml
echo Setting up test case: %case%
%python% setup_test.py -o %output% %case%
cd /d %output%
echo Deploying...
%python% %~dp0..\main.py deploy
echo Unpacking...
%python% %~dp0..\main.py unpack
popd
pause
