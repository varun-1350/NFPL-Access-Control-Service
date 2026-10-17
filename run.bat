@echo off
title Nagarkot Access Control Platform - Web Application
cls

echo =========================================================================
echo               NAGARKOT ACCESS CONTROL PLATFORM (NFPL)
echo =========================================================================
echo.
echo [1/3] Initializing and verifying SQLite database...
python seed_demo.py
if errorlevel 1 (
    echo [ERROR] Database initialization failed. Please check Python environment.
    pause
    exit /b 1
)

echo.
echo [2/3] Launching web application in your default browser...
start "" "http://localhost:5000"

echo.
echo [3/3] Starting Python web server on http://localhost:5000...
echo (Press Ctrl+C to stop the server at any time)
echo =========================================================================
echo.
python server.py

pause
