@echo off
title ARYA Daemon - Hardware Control
cd /d C:\Users\nagas\Documents\PROJECTS\ARYA
echo Starting ARYA Daemon...
C:\Users\nagas\Documents\PROJECTS\ARYA\.venv\Scripts\python.exe daemon\arya_daemon.py --node-id laptop-primary --server http://localhost:8000
pause
