@echo off
chcp 65001 >nul
echo ========================================
echo    ZTXAI - Installing Dependencies
echo ========================================
echo.

pip install -r requirements.txt

echo.
echo ========================================
echo    Installation Complete!
echo ========================================
pause
