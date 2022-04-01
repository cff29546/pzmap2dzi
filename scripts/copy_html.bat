pushd %~dp0..
set /p out_path= <out_path.txt
xcopy /Q /E /I /Y html "%out_path%\html"
popd