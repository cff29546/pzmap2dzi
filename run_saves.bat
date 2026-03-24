@echo off
pushd %~dp0

python main.py deploy
python main.py unpack
python main.py render save save_top
echo All done
popd
pause
