@echo off
setlocal
cd /d "%~dp0"

echo Starting RetroTap GUI...
echo.

REM Prefer the Windows Python launcher if available.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 retrotap_control_panel.py
    goto :end
)

REM Try normal python if available.
where python >nul 2>nul
if %errorlevel%==0 (
    python retrotap_control_panel.py
    goto :end
)

REM Try common Anaconda locations for this PC/user.
if exist "%USERPROFILE%\anaconda3\python.exe" (
    "%USERPROFILE%\anaconda3\python.exe" retrotap_control_panel.py
    goto :end
)

if exist "%USERPROFILE%\miniconda3\python.exe" (
    "%USERPROFILE%\miniconda3\python.exe" retrotap_control_panel.py
    goto :end
)

if exist "C:\ProgramData\anaconda3\python.exe" (
    "C:\ProgramData\anaconda3\python.exe" retrotap_control_panel.py
    goto :end
)

echo Python could not be found.
echo.
echo Try editing this BAT file and replacing the python line with the exact path
echo to the Python that works for your terminal BAT.
echo.
echo Example:
echo "C:\Users\YOURNAME\anaconda3\python.exe" retrotap_control_panel.py
echo.

:end
pause
