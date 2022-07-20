pushd %~dp0..
for /f "delims=" %%x in (config.txt) do set %%x

xcopy /Q /E /I /Y html "%out_path%\html"
popd