@echo off
setlocal

set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "BACKEND_ERR=%LOG_DIR%\backend.error.log"
set "FRONTEND_ERR=%LOG_DIR%\frontend.error.log"

echo Starting backend and frontend...
echo Error logs folder: %LOG_DIR%

echo Backend errors: %BACKEND_ERR%
echo Frontend errors: %FRONTEND_ERR%

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo [Backend] Stopping existing process on port 8000, PID=%%p ...
  taskkill /F /PID %%p >nul 2>&1
)

start "ResearchBridge Backend" cmd /k "cd /d ""%ROOT%"" && call ""%ROOT%backend_start.bat"" 2>>""%BACKEND_ERR%"""
start "ResearchBridge Frontend" cmd /k "cd /d ""%ROOT%"" && call ""%ROOT%frontend_start.bat"" 2>>""%FRONTEND_ERR%"""

echo Done. Two windows should be open:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:5173

endlocal
