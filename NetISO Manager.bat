@echo off
rem Opens NetISO Manager without a console window.
set "PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw.exe"
start "" "%PYW%" "%~dp0app\NetISOManager.pyw"
