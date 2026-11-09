@echo off
setlocal
rem Lot Structure: double-click to open the window.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First-time setup: creating the Python environment...
    where py >nul 2>&1
    if errorlevel 1 (
        call :makevenv python
        if errorlevel 1 goto :error
    ) else (
        call :makevenv py
        if errorlevel 1 goto :error
    )
)
rem Install again whenever pyproject.toml changed (a new version was copied in).
fc /b pyproject.toml ".venv\pyproject.installed" >nul 2>&1
if errorlevel 1 (
    echo Installing the packages, this takes a minute the first time...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -e . || goto :error
    copy /y pyproject.toml ".venv\pyproject.installed" >nul
)
rem pythonw shows nothing: check here first that the window can start at all
".venv\Scripts\python.exe" -c "import lot_structure.gui" || goto :error
start "" ".venv\Scripts\pythonw.exe" -m lot_structure || goto :error
exit /b 0
:error
set "ERR=%errorlevel%"
echo.
echo Lot Structure could not start. See the message above.
pause
exit /b %ERR%

:makevenv
rem Create the Python environment with %~1 (py or python); needs 3.10 or newer.
where %~1 >nul 2>&1
if errorlevel 1 (
    echo No Python found. Install Python 3.10 or newer from https://www.python.org/downloads/ and try again.
    exit /b 1
)
%~1 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo This PC's Python is missing or too old. Install Python 3.10 or newer and try again.
    exit /b 1
)
%~1 -m venv .venv
exit /b
