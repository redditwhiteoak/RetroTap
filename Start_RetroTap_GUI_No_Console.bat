@echo off
setlocal
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
    pyw -3 Start_RetroTap_GUI.pyw
    exit /b
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    pythonw Start_RetroTap_GUI.pyw
    exit /b
)

if exist "%USERPROFILE%\anaconda3\pythonw.exe" (
    "%USERPROFILE%\anaconda3\pythonw.exe" Start_RetroTap_GUI.pyw
    exit /b
)

if exist "%USERPROFILE%\miniconda3\pythonw.exe" (
    "%USERPROFILE%\miniconda3\pythonw.exe" Start_RetroTap_GUI.pyw
    exit /b
)

echo Could not find pythonw/pyw.
pause
