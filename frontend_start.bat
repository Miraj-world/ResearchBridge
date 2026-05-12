@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND_DIR=%ROOT%frontend"

cd /d "%FRONTEND_DIR%"

echo [Frontend] Working directory: %FRONTEND_DIR%
echo [Frontend] Starting on http://localhost:5173
npm run dev
