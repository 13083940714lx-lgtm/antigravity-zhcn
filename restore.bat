@echo off
chcp 65001 >nul
setlocal
set "PY=python"
where python >nul 2>nul || set "PY=py"
if not "%~1"=="" set "PY=%~1"
echo ============================================
echo   Antigravity - 杩樺師瀹樻柟鑻辨枃鍘熺増
echo ============================================
"%PY%" "%~dp0install.py" restore --close
echo.
pause
