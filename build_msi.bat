@echo off
rem Builds dist\NetISOManager-<version>-x64.msi: the app, its launcher and the user guides.
rem Needs Python 3 and the WiX command line tool with its firewall extension:
rem   dotnet tool install --global wix --version 5.0.2
rem   wix extension add -g WixToolset.Firewall.wixext/5.0.2
setlocal
cd /d "%~dp0"
set VERSION=1.1.0
if not exist build_env\Scripts\python.exe python -m venv build_env || exit /b 1
build_env\Scripts\python.exe -m pip install --disable-pip-version-check pyinstaller || exit /b 1
build_env\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed ^
    --name "NetISO Manager" --paths "%~dp0app" --add-data "%~dp0app\stub.xex;." ^
    --add-data "%~dp0docs;docs" --add-data "%~dp0app\plugin;plugin" --distpath "%~dp0dist\onedir" ^
    --workpath "%~dp0build_env\work" --specpath "%~dp0build_env" ^
    "%~dp0app\NetISOManager.pyw" || exit /b 1
wix build -arch x64 -ext WixToolset.Firewall.wixext -d Version=%VERSION% -d "Source=%~dp0dist\onedir\NetISO Manager" ^
    -o "%~dp0dist\NetISOManager-%VERSION%-x64.msi" "%~dp0installer\NetISOManager.wxs"
