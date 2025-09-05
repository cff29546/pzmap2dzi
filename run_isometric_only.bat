@echo off
pushd %~dp0

python main.py deploy
python main.py unpack
python main.py render base zombie foraging rooms objects streets

echo All done
popd
pause