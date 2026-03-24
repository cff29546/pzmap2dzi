@echo off
setlocal enabledelayedexpansion
set case=%1
if "%case%"=="" (
    echo Please specify a test case.
    exit /b 1
)

rem for comaptibility with old test cases
if "%case%"=="1" set args=base base_top
if "%case%"=="2" set args=zombie zombie_top
if "%case%"=="3" set args=rooms objects streets
if "%case%"=="4" set args=foraging foraging_top

if "%case%"=="b" set args=base base_top
if "%case%"=="bi" set args=base
if "%case%"=="bt" set args=base_top

if "%case%"=="z" set args=zombie zombie_top
if "%case%"=="zi" set args=zombie
if "%case%"=="zt" set args=zombie_top

if "%case%"=="o" set args=rooms objects streets

if "%case%"=="f" set args=foraging foraging_top
if "%case%"=="fi" set args=foraging
if "%case%"=="ft" set args=foraging_top

if "%case%"=="s" set args=save save_top
if "%case%"=="si" set args=save
if "%case%"=="st" set args=save_top

if "%case%"=="all" set args=base base_top zombie zombie_top rooms objects streets foraging foraging_top

for /f "delims=" %%x in (env.txt) do set %%x
echo Running test case: %args%
start "" /d "%output%" cmd /c "%python% %~dp0..\main.py render %args% & pause"