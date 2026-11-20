@echo off
rem Double-click to start SPBM. The first start installs the Python packages
rem (a few minutes, needs Python 3.10 or later from python.org). After that it
rem starts in seconds, opens the page in your browser, and stops by itself
rem about 15 minutes after the page is closed (never during a run).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First start: setting up SPBM. This takes a few minutes, once.
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo Python 3.10 or later is needed. Install it from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo Installing the packages failed - see the messages above.
    pause
    exit /b 1
  )
)
start "SPBM (close this window to stop)" /min ".venv\Scripts\python.exe" -m spbm serve --open --idle-exit 15
