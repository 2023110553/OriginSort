@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m PyInstaller OriginSort.spec --clean --noconfirm
if errorlevel 1 exit /b %errorlevel%
echo Build complete: %CD%\dist\OriginSort.exe

