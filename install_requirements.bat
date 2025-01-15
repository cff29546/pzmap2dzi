python -c "import sys; exit(sys.version_info[0])"
if "%ERRORLEVEL%" == "3" (
    python -m pip install -r "%~dp0requirements.txt"
) else (
    if "%ERRORLEVEL%" == "2" (
        python -m pip install -r "%~dp0requirements_python2.txt"
    ) else (
        echo missing python2 or python3
    )
)
pause