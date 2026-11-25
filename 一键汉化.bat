@echo off
chcp 65001 >nul
setlocal
set "PY=python"
where python >nul 2>nul || set "PY=py"
if not "%~1"=="" set "PY=%~1"
echo ============================================
echo   Antigravity 中文汉化 - 一键安装
echo ============================================
"%PY%" "%~dp0install.py" install --close
echo.
pause
