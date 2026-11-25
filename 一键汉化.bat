@echo off
chcp 65001 >nul
setlocal
set "PY=python"
where python >nul 2>nul || set "PY=py"
if not "%~1"=="" set "PY=%~1"
echo ============================================
echo   Antigravity 涓枃姹夊寲 - 涓€閿畨瑁?echo ============================================
"%PY%" "%~dp0install.py" install --close
echo.
pause
