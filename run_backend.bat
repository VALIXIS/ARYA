@echo off
title ARYA Backend - FastAPI :8000
set PATH=%LOCALAPPDATA%\Android\Sdk\platform-tools;%PATH%
cd /d C:\Users\nagas\Documents\PROJECTS\ARYA\backend
echo Starting ARYA Backend...
C:\Users\nagas\Documents\PROJECTS\ARYA\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000
pause
