@echo off
chcp 65001 >nul
setlocal
set "PY=python"
where python >nul 2>nul || set "PY=py"
if not "%~1"=="" set "PY=%~1"
echo ============================================
echo   Antigravity - 还原官方英文原版
echo ============================================
"%PY%" "%~dp0install.py" restore --close
echo.
pause
