@echo off
setlocal EnableDelayedExpansion

REM Base directory containing the 5 parent folders
set "BASE_DIR=D:\viji\viji-olivine"

:MAIN_MENU
echo.
echo ========================================
echo    SELECT PARENT FOLDER
echo ========================================
echo.
echo   1. 00current
echo   2. 01nextphase
echo   3. 02reference
echo   4. 03rolledout
echo   5. 04research
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
goto MAIN_MENU

:SHOW_SUBFOLDERS
echo.
echo ========================================
echo    SUBFOLDERS IN %PARENT%
echo ========================================
echo.

set "CURRENT_PATH=%BASE_DIR%\%PARENT%"
cd /d "%CURRENT_PATH%"

REM List subfolders with numbers
set "count=0"
for /d %%F in (*) do (
    set /a "count+=1"
    set "folder!count!=%%F"
    echo   !count!. %%F
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
    goto SHOW_SUBFOLDERS
)

echo.
echo Selected: %CURRENT_PATH%\!selected!
cd /d "%CURRENT_PATH%\!selected!"
echo Current directory: %CD%
echo.

REM Run git commands in selected folder
call :GIT_PUSH

goto MAIN_MENU

:GIT_PUSH
echo ========================================
echo    GIT PUSH IN %CD%
echo ========================================
echo.

if not exist ".git" (
    echo Initializing git repository...
    git init
) else (
    echo Git repository already initialized.
)

echo.
echo Adding all files to staging...
git add .

echo.
set /p "commit_msg=Enter commit message: "

git commit -m "%commit_msg%"

echo.
git remote -v >nul 2>&1
if %errorlevel% neq 0 (
    set /p "remote_url=Enter remote repository URL: "
    git remote add origin "%remote_url%"
)

echo.
echo Pushing to origin main...
git push -u origin main 2>nul || git push -u origin master 2>nul

echo.
echo Done!
echo.
pause
goto :eof
