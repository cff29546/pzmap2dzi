@echo off
pushd %~dp0

python main.py deploy
python main.py unpack
python main.py render base zombie foraging room objects

echo All done
popd
pause