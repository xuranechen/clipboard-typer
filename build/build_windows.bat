@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
python -m pip install -r requirements.txt
if exist "assets\icon.ico" (
    pyinstaller -F -w -n ClipboardTyper -i assets\icon.ico --version-file build\version.txt --collect-data ttkbootstrap main.py
) else (
    pyinstaller -F -w -n ClipboardTyper --version-file build\version.txt --collect-data ttkbootstrap main.py
)
pause
