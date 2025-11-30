@echo off
setlocal enabledelayedexpansion

:: Set Python command (assuming python is in PATH)
set PYTHON_CMD=python

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Go to project root (parent of scripts)
cd /d "%SCRIPT_DIR%\.."
set "PROJECT_ROOT=%CD%"

echo [Step 1] Preparing A-Stock Data...
cd data\A_stock
%PYTHON_CMD% get_daily_price_xtquant.py
%PYTHON_CMD% merge_jsonl_xtquant.py
echo Done.
pause