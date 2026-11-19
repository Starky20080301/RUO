@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found.
    echo         Please install Python 3.9 or newer and tick "Add Python to PATH",
    echo         then run this file again. See README.md for details.
    echo.
    pause
    exit /b 1
)

python -c "import PIL, requests" >nul 2>nul
if errorlevel 1 (
    echo.
    echo First run: installing dependencies Pillow and requests ...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies. Check your network and try again.
        echo.
        pause
        exit /b 1
    )
)

start "" pythonw main.py
exit /b 0
