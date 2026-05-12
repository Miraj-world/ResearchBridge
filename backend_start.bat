@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_PY=%ROOT%backend\.venv\Scripts\python.exe"

cd /d "%ROOT%"

echo [Backend] Working directory: %ROOT%

if not exist "%BACKEND_PY%" (
  echo [Backend] Missing virtual environment Python at:
  echo %BACKEND_PY%
  echo [Backend] Create it with:
  echo py -3.12 -m venv backend\.venv
  echo backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  exit /b 1
)

echo [Backend] Using interpreter: %BACKEND_PY%
echo [Backend] Running dependency preflight...
"%BACKEND_PY%" backend\tools\preflight_check.py
if errorlevel 1 (
  echo [Backend] Preflight failed. Backend will not start.
  exit /b 1
)

echo [Backend] Starting on http://localhost:8000
"%BACKEND_PY%" -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
