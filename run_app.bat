@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Shift Signal needs Python 3.10 or newer.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating Shift Signal's private Python environment...
  py -m venv .venv
)
".venv\Scripts\python.exe" -c "import streamlit, plotly" >nul 2>&1
if errorlevel 1 (
  echo Installing Shift Signal's open-source packages...
  ".venv\Scripts\python.exe" -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
if not defined ARROW_DEFAULT_MEMORY_POOL set ARROW_DEFAULT_MEMORY_POOL=system
if "%SHIFTSIGNAL_PORT%"=="" set SHIFTSIGNAL_PORT=8596
echo Starting Shift Signal at http://127.0.0.1:%SHIFTSIGNAL_PORT% ...
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=%SHIFTSIGNAL_PORT% --server.maxUploadSize=20 --server.fileWatcherType=none --browser.gatherUsageStats=false
if errorlevel 1 pause
