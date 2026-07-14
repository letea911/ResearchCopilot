@echo off
chcp 65001 >nul
cd /d %~dp0
set PYTHONPATH=%~dp0
set PY=C:\ProgramData\anaconda3\python.exe
set LOG=%~dp0gui_error.log

echo ==== launch %date% %time% ==== > "%LOG%"
if not exist "%PY%" (
    echo [ERROR] anaconda python not found: %PY% >> "%LOG%"
    type "%LOG%"
    pause
    exit /b 1
)

"%PY%" -m gui.main >> "%LOG%" 2>&1
echo ExitCode=%errorlevel% >> "%LOG%"

if errorlevel 1 (
    echo.
    echo [program crashed] see gui_error.log
    type "%LOG%"
    pause
)
