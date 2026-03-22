@echo off
REM Simple git push script for a new folder

echo Initializing git repository (if not already done)...
git init

echo.
echo Adding all files to staging...
git add .

echo.
set /p commit_msg="Enter commit message: "

git commit -m "%commit_msg%"

echo.
echo Checking if remote origin exists...
git remote -v >nul 2>&1
if %errorlevel% neq 0 (
    set /p remote_url="Enter remote repository URL: "
    git remote add origin "%remote_url%"
)

echo.
echo Pushing to origin main...
git push -u origin main

echo.
echo Done!
pause
