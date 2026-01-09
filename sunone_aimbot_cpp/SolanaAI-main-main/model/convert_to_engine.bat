@echo off
setlocal EnableDelayedExpansion

REM Default color: Green
color 0A

cd /d "%~dp0"

REM Clear screen before displaying menu
cls

REM List .pt files
set "i=0"
for /f "delims=" %%F in ('dir /b /a:-d "*.pt" 2^>nul') do (
    set /a i+=1
    set "file[!i!]=%%~nxF"
)

if %i%==0 (
    echo No .pt files found in "%cd%".
    pause
    exit /b 1
)

echo Available models (.pt files):
for /l %%N in (1,1,%i%) do (
    echo   %%N^) !file[%%N]!
)

REM Switch to yellow for selection prompt
color 0E
:select
set /p "choice=What model do you want to choose? Enter number (1-%i%): "
color 0A
cls
if not defined file[%choice%] (
    color 0E
    echo Invalid selection. Try again.
    color 0A
    goto select
)
set "selected=!file[%choice%]!"

REM Prompt for image size
color 0E
:imgsz
set /p "imgsize=Insert image size (320 or 640): "
color 0A
cls
if /i not "%imgsize%"=="320" if /i not "%imgsize%"=="640" (
    color 0E
    echo Invalid image size. Only 320 or 640 allowed.
    color 0A
    goto imgsz
)

echo Running: yolo export model="%selected%" format="engine" imgsz=%imgsize%
yolo export model="%selected%" format="engine" imgsz=%imgsize%
