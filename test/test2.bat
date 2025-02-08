pushd %~dp0
for /f "delims=" %%x in (env.txt) do set %%x
cd /d %output%
%python% %~dp0..\main.py render zombie zombie_top
popd
pause