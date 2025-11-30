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

echo Launching AI Trader Environment...

echo [1/4] Getting and merging price data...
cd data
call %PYTHON_CMD% get_daily_price.py
call %PYTHON_CMD% merge_jsonl.py
cd ..

echo [2/4] Starting MCP services...
cd agent_tools
:: Note: If start_mcp_services.py blocks, the script will pause here.
call %PYTHON_CMD% start_mcp_services.py
cd ..

timeout /t 2 /nobreak >nul

echo [3/4] Starting main trading agent...
call %PYTHON_CMD% main.py configs/default_config.json

echo [4/4] Starting web server...
cd docs
call %PYTHON_CMD% -m http.server 8888
pause