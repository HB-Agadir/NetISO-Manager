@echo off
rem Builds dist\NetISO Manager.exe, a standalone executable that needs no Python install.
rem Needs Python 3 on the PATH; PyInstaller is installed into a local build_env folder.
setlocal
cd /d "%~dp0"
if not exist build_env\Scripts\python.exe python -m venv build_env || exit /b 1
build_env\Scripts\python.exe -m pip install --disable-pip-version-check pyinstaller || exit /b 1
build_env\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "NetISO Manager" --paths "%~dp0app" --add-data "%~dp0app\stub.xex;." ^
    --distpath "%~dp0dist" --workpath "%~dp0build_env\work" --specpath "%~dp0build_env" ^
    "%~dp0app\NetISOManager.pyw"
