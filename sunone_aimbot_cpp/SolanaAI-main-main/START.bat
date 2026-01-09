@echo off
:: Solana AI Launcher with Admin Elevation
:: This script automatically requests admin privileges if not already elevated

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :hasAdmin
) else (
    goto :requestAdmin
)

:requestAdmin
    echo Requesting administrator privileges...
    echo.
    
    :: Create a temporary VBScript to elevate privileges
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    
    :: Run the VBScript
    "%temp%\getadmin.vbs"
    
    :: Clean up
    del "%temp%\getadmin.vbs"
    
    :: Exit the current (non-elevated) instance
    exit /B

:hasAdmin
    :: Running with admin privileges
    pushd "%CD%"
    CD /D "%~dp0"
    
    :: Clear screen and show status
    cls
    echo ========================================
    echo     Solana AI - Administrator Mode
    echo ========================================
    echo.
    echo [+] Running with administrator privileges
    echo [+] Starting Solana AI...
    echo.
    
    :: Check if Python is installed
    python --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo [-] Error: Python is not installed or not in PATH
        echo.
        echo Please install Python and try again.
        pause
        exit /B 1
    )
    
    :: Check if detector.py exists
    if not exist "detector.py" (
        echo [-] Error: detector.py not found in current directory
        echo.
        echo Please ensure you're running this from the correct folder.
        pause
        exit /B 1
    )
    
    :: Run the Python script
    python detector.py
    
    :: Check if Python script exited with error
    if %errorLevel% neq 0 (
        echo.
        echo [-] Solana AI exited with error code: %errorLevel%
        echo.
        pause
    )
    
    exit /B %errorLevel%