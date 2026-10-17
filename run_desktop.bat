@echo off
title Nagarkot Access Control Platform - Desktop GUI
cls

echo =========================================================================
echo       NAGARKOT ACCESS CONTROL PLATFORM - CUSTOMTKINTER DESKTOP GUI
echo =========================================================================
echo.
echo Initializing database and launching Desktop application...
python seed_demo.py
python app.py
pause
