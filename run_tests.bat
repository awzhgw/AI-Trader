@echo off
REM Windows script to run broker tests
REM Usage: run_tests.bat [pytest arguments]
REM Example: run_tests.bat -k "test_detect_market"

setlocal

REM Set project root to current directory
set "PROJECT_ROOT=%~dp0"
set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"

echo ============================================================
echo Running Broker Tests on Windows
echo ============================================================

pytest -v "%PROJECT_ROOT%tests" %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] All tests passed.
) else (
    echo.
    echo [FAILURE] Tests failed with exit code %ERRORLEVEL%.
)

endlocal
exit /b %ERRORLEVEL%
