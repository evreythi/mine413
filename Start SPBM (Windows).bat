@echo off
rem Double-click to start SPBM. The first start sets everything up (a few
rem minutes, once): it finds Python 3.10 or later, or installs Python 3.13 for
rem your user account if there is none, then installs the packages. After that
rem SPBM starts in seconds, opens in your browser, and stops by itself about
rem 15 minutes after the page is closed (never during a run).
setlocal
cd /d "%~dp0"
rem PyYAML has no ready-made build for the newest Python versions; this makes
rem it install as plain Python instead of needing a C++ compiler.
set PYYAML_FORCE_LIBYAML=0
if exist ".venv\spbm_ready.txt" goto start
echo Setting up SPBM. This takes a few minutes, once.
if exist ".venv\Scripts\python.exe" goto packages

call :findpython
if defined PYEXE goto makevenv
echo Python was not found. Installing Python 3.13 for your user account (no administrator rights needed)...
winget install -e --id Python.Python.3.13 --scope user --silent --accept-package-agreements --accept-source-agreements
call :findpython
if defined PYEXE goto makevenv
echo winget could not install it; downloading the installer from python.org instead...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f = Join-Path $env:TEMP 'python-3.13-installer.exe'; Invoke-WebRequest 'https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe' -OutFile $f; Start-Process $f -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1' -Wait"
call :findpython
if defined PYEXE goto makevenv
echo Python could not be installed automatically. Install Python 3.13 from https://www.python.org/downloads/ and double-click this file again.
pause
exit /b 1

:makevenv
echo Using %PYEXE%
"%PYEXE%" -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Could not create the Python environment - see the messages above.
  pause
  exit /b 1
)

:packages
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Installing the packages failed - see the messages above.
  pause
  exit /b 1
)
echo ready> ".venv\spbm_ready.txt"

:start
start "SPBM (close this window to stop)" /min ".venv\Scripts\python.exe" -m spbm serve --open --idle-exit 15
exit /b 0

rem Sets PYEXE to a Python 3.10 or later: 3.13 first (every package has a
rem ready-made build for it), then other versions, then the usual install folder.
:findpython
set "PYEXE="
for %%v in (3.13 3.12 3.14 3.11 3.10 3.15) do call :trypy %%v
if defined PYEXE exit /b 0
for /f "delims=" %%p in ('python -c "import sys; sys.version_info >= (3, 10) and print(sys.executable)" 2^>nul') do set "PYEXE=%%p"
if defined PYEXE exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
exit /b 0

:trypy
if defined PYEXE exit /b 0
for /f "delims=" %%p in ('py -%1 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%p"
exit /b 0
