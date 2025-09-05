@echo off
pushd %~dp0

python main.py deploy
python main.py unpack
python main.py render base_top zombie_top foraging_top rooms objects streets

echo All done
popd
pause
