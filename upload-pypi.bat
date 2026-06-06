@echo off
cd /d "%~dp0"
echo.
echo split-stack - upload to REAL PyPI (pypi.org token)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\upload-pypi.ps1"
echo.
pause
