@echo off
:: build-windows.bat — FOR DEVELOPMENT / CI USE ONLY
:: Produces file-organizer\dist\FileSwipper\
::
:: Run from repo root on a Windows machine with Python 3.10+ installed.
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%file-organizer
set BUILD_VENV=%SCRIPT_DIR%.build-venv

echo === FileSwipper Windows Build ===

if not exist "%BUILD_VENV%" (
    echo Creating build virtual environment...
    python -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo ERROR: python not found. Install Python 3.10+ and add to PATH.
        exit /b 1
    )
)

call "%BUILD_VENV%\Scripts\activate.bat"

echo Installing build dependencies...
pip install --quiet --upgrade pip
pip install --quiet pyinstaller
pip install --quiet -r "%APP_DIR%\requirements.txt"

echo Running PyInstaller...
cd /d "%APP_DIR%"
pyinstaller fileswipper.spec --clean --noconfirm

echo.
echo Build complete: %APP_DIR%\dist\FileSwipper\
echo Test it: double-click %APP_DIR%\dist\FileSwipper\FileSwipper.exe
