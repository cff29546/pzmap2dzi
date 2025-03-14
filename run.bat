@echo off
pushd %~dp0

python main.py deploy
python main.py unpack
python main.py render base base_top zombie zombie_top foraging foraging_top room objects

echo All done
popd
pause
