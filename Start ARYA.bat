@echo off
chcp 65001 >nul
title PROJECT ARYA Launcher
cd /d C:\Users\nagas\Documents\PROJECTS\ARYA

set PATH=%LOCALAPPDATA%\Android\Sdk\platform-tools;%PATH%

echo.
echo ============================================================
echo    PROJECT ARYA - AUTONOMOUS PERSONAL AI ASSISTANT
echo ============================================================
echo.

echo Cleaning up any old background instances...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo [1/3] Starting Backend...
start "ARYA Backend" C:\Users\nagas\Documents\PROJECTS\ARYA\run_backend.bat

echo Waiting for backend (8s)...
timeout /t 8 /nobreak >nul

echo [2/3] Starting Frontend...
start "ARYA Frontend" C:\Users\nagas\Documents\PROJECTS\ARYA\run_frontend.bat

echo Waiting for frontend (10s)...
timeout /t 10 /nobreak >nul

echo [3/3] Starting Daemon...
start "ARYA Daemon" C:\Users\nagas\Documents\PROJECTS\ARYA\run_daemon.bat

echo Opening browser...
timeout /t 2 /nobreak >nul
start "" http://localhost:5173

echo.
echo ============================================================
echo  DONE - Backend, Frontend and Daemon are running!
echo  Open: http://localhost:5173
echo ============================================================
timeout /t 5
