@echo off
rem Zaroni Virtual Instruments launcher for Windows.
rem Creates a local virtual environment (.venv) on first run, installs the
rem dependencies when requirements.txt changes, then starts the application.
setlocal
cd /d "%~dp0"

rem Find a Python 3.10+ interpreter (the "py" launcher first, then "python").
set "PYTHON="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1 && set "PYTHON=py -3"
if not defined PYTHON (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON (
    echo Error: Python 3.10 or newer is required.
    echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

rem Create the virtual environment on first run.
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv ...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Error: could not create the virtual environment.
        pause
        exit /b 1
    )
)
set "VENV_PY=.venv\Scripts\python.exe"

rem Install dependencies when requirements.txt is new or has changed.
set "STAMP=.venv\.requirements.installed"
set "NEED_INSTALL=1"
if exist "%STAMP%" (
    fc /b requirements.txt "%STAMP%" >nul 2>&1 && set "NEED_INSTALL=0"
)
if "%NEED_INSTALL%"=="1" (
    echo Installing dependencies ...
    "%VENV_PY%" -m pip install --upgrade pip --quiet
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: dependency installation failed.
        pause
        exit /b 1
    )
    copy /y requirements.txt "%STAMP%" >nul
)

"%VENV_PY%" main.py %*
if errorlevel 1 pause
endlocal
