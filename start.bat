@echo off
setlocal

set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "FRONTEND_DIR=%ROOT%frontend"
set "BACKEND_PY=%ROOT%backend\.venv\Scripts\python.exe"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "BACKEND_ERR=%LOG_DIR%\backend.error.log"
set "FRONTEND_ERR=%LOG_DIR%\frontend.error.log"

echo Starting backend and frontend...
echo Error logs folder: %LOG_DIR%

echo Backend errors: %BACKEND_ERR%
echo Frontend errors: %FRONTEND_ERR%

if not exist "%BACKEND_PY%" (
  echo [Backend] Missing virtual environment Python at:
  echo %BACKEND_PY%
  echo Create it with:
  echo py -3.12 -m venv backend\.venv
  echo backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  goto :START_FRONTEND
)

start "ResearchBridge Backend" cmd /k "cd /d ""%ROOT%"" && echo [Backend] Using %BACKEND_PY% && echo [Backend] Running dependency preflight... && ""%BACKEND_PY%"" backend\tools\preflight_check.py && echo [Backend] Starting on http://localhost:8000 && ""%BACKEND_PY%"" -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000 2>>""%BACKEND_ERR%"""

:START_FRONTEND
start "ResearchBridge Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && echo [Frontend] Starting on http://localhost:5173 && npm run dev 2>>""%FRONTEND_ERR%"""

echo Done. Two windows should be open:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:5173

endlocal
