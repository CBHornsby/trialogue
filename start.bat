@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Trialogue Launcher - Windows
REM Starts the Python backend and Next.js frontend, opens browser.
REM ============================================================

echo.
echo  Starting Trialogue...
echo.

REM Get the directory where this script lives
set "ROOT=%~dp0"
cd /d "%ROOT%"

REM ------------------------------------------------------------
REM Verify Python is installed
REM ------------------------------------------------------------
where python >nul 2>nul
if errorlevel 1 goto :no_python
goto :check_node

:no_python
echo ERROR: Python is not installed or not in PATH.
echo Install from https://python.org and check "Add to PATH" during install.
pause
exit /b 1

REM ------------------------------------------------------------
REM Verify Node is installed
REM ------------------------------------------------------------
:check_node
where node >nul 2>nul
if errorlevel 1 goto :no_node
goto :check_backend

:no_node
echo ERROR: Node.js is not installed or not in PATH.
echo Install from https://nodejs.org
pause
exit /b 1

REM ------------------------------------------------------------
REM First-time setup: backend
REM ------------------------------------------------------------
:check_backend
if exist "backend\venv" goto :check_frontend

echo  First-time setup: creating Python virtual environment...
cd backend
python -m venv venv
if errorlevel 1 goto :venv_failed
call venv\Scripts\activate.bat
echo  Installing Python dependencies...
pip install -q -r requirements.txt
if errorlevel 1 goto :pip_failed
cd ..
goto :check_frontend

:venv_failed
echo ERROR: Failed to create Python virtual environment.
cd ..
pause
exit /b 1

:pip_failed
echo ERROR: Failed to install Python dependencies.
cd ..
pause
exit /b 1

REM ------------------------------------------------------------
REM First-time setup: frontend
REM ------------------------------------------------------------
:check_frontend
if exist "frontend\node_modules" goto :start_servers

echo  First-time setup: installing frontend dependencies. This takes a minute...
cd frontend
call npm install
if errorlevel 1 goto :npm_failed
cd ..
goto :start_servers

:npm_failed
echo ERROR: Failed to install frontend dependencies.
cd ..
pause
exit /b 1

REM ------------------------------------------------------------
REM Start servers
REM ------------------------------------------------------------
:start_servers
echo  Starting backend on port 8000...
start "Trialogue Backend" cmd /k "cd /d %ROOT%backend && venv\Scripts\activate.bat && python main.py"

timeout /t 3 /nobreak >nul

echo  Starting frontend on port 3000...
start "Trialogue Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

timeout /t 5 /nobreak >nul

echo  Opening browser...
start http://localhost:3000

echo.
echo  Trialogue is running.
echo  Close the backend and frontend windows to stop.
echo.
pause
