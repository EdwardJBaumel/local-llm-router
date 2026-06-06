@echo off
cd /d "%~dp0"
echo.
echo local-llm-router - upload to TestPyPI (test.pypi.org token)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\upload-pypi.ps1" -TestPyPI
echo.
pause
