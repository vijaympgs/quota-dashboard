@echo off
setlocal EnableDelayedExpansion

REM Base directory containing the 5 parent folders
set "BASE_DIR=D:\viji\viji-olivine"

:MAIN_MENU
cls
echo ========================================
echo    SELECT WORK FOLDER
echo ========================================
echo.
echo   1. 00current
echo   2. 01nextphase
echo   3. 02reference
echo   4. 03rolledout
echo   5. 04research
echo.
echo   0. Exit
echo.
set /p "choice=Enter number (0-5): "

if "%choice%"=="0" exit /b
if "%choice%"=="1" set "PARENT=00current" & goto SHOW_SUBFOLDERS
if "%choice%"=="2" set "PARENT=01nextphase" & goto SHOW_SUBFOLDERS
if "%choice%"=="3" set "PARENT=02reference" & goto SHOW_SUBFOLDERS
if "%choice%"=="4" set "PARENT=03rolledout" & goto SHOW_SUBFOLDERS
if "%choice%"=="5" set "PARENT=04research" & goto SHOW_SUBFOLDERS

echo Invalid choice. Try again.
pause
goto MAIN_MENU

:SHOW_SUBFOLDERS
cls
echo ========================================
echo    SUBFOLDERS IN %PARENT%
echo ========================================
echo.

set "CURRENT_PATH=%BASE_DIR%\%PARENT%"

REM List subfolders with numbers
set "count=0"
for /d %%F in ("%CURRENT_PATH%\*") do (
    set /a "count+=1"
    set "folder!count!=%%~nxF"
    echo   !count!. %%~nxF
)

echo.
echo   0. Go back
echo.
set /p "subchoice=Enter number (0-%count%): "

if "%subchoice%"=="0" goto MAIN_MENU

REM Validate choice
set "selected=!folder%subchoice%!"
if "!selected!"=="" (
    echo Invalid choice. Try again.
    pause
    goto SHOW_SUBFOLDERS
)

set "TARGET_FOLDER=%CURRENT_PATH%\!selected!"
echo.
echo Opening: %TARGET_FOLDER%

REM Open the folder in VS Code
code "%TARGET_FOLDER%"

exit /b
