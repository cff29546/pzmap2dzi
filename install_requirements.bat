pushd %~dp0
for /f "delims=" %%x in (config.txt) do set %%x

%py% -m pip install -r "%~dp0requirements.txt"
popd