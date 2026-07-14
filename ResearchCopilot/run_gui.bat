@echo off
chcp 65001 >nul
cd /d %~dp0
set PYTHONPATH=%~dp0

rem 写死用 Anaconda 的 python（项目依赖都装在这里）。
rem 直接用 python 可能指到没装库的 Python312 → 导入失败闪退。
set PY=C:\ProgramData\anaconda3\python.exe

if not exist "%PY%" (
    echo [错误] 找不到 Anaconda python: %PY%
    echo 请打开本文件，把上面的 PY 改成你自己的 python.exe 完整路径。
    pause
    exit /b 1
)

"%PY%" -m gui.main

rem 如果上面出错，pause 让窗口停住，方便看报错（正常关闭窗口不受影响）。
if errorlevel 1 (
    echo.
    echo [程序异常退出] 请把上面的报错信息发给开发者。
    pause
)
