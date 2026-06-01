@echo off
REM Prarambha Vercel Production Deployment Script
REM This script commits and pushes all changes to GitHub

echo.
echo ====================================================
echo  Prarambha - Production Deployment Script
echo ====================================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git: https://git-scm.com/download/win
    exit /b 1
)

REM Check if we're in a git repository
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo ERROR: Not a git repository
    echo Please run: git init
    exit /b 1
)

REM Display current status
echo Current Git Status:
echo.
git status --short
echo.

REM Confirm before proceeding
set /p confirm="Continue with deployment? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Deployment cancelled.
    exit /b 0
)

echo.
echo Step 1: Adding all files...
git add -A
if errorlevel 1 (
    echo ERROR: Failed to add files
    exit /b 1
)
echo ✓ Files staged

echo.
echo Step 2: Creating commit...
git commit -m "Production deployment: Fix Vercel 500 errors, add comprehensive error handling, optimize database operations"
if errorlevel 1 (
    echo ERROR: Failed to create commit
    exit /b 1
)
echo ✓ Commit created

echo.
echo Step 3: Pushing to GitHub...
git push origin main
if errorlevel 1 (
    echo WARNING: Push to main failed. Trying master branch...
    git push origin master
    if errorlevel 1 (
        echo ERROR: Failed to push changes
        echo Please verify your git configuration and try again
        exit /b 1
    )
)
echo ✓ Changes pushed to GitHub

echo.
echo Step 4: Deploying to Vercel...
vercel --prod
if errorlevel 1 (
    echo WARNING: Vercel deployment command failed
    echo Please deploy manually:
    echo   - Go to https://vercel.com
    echo   - Select your project
    echo   - Deploy from git
)

echo.
echo ====================================================
echo  ✓ Deployment Process Complete!
echo ====================================================
echo.
echo Next steps:
echo 1. Check Vercel deployment status at: https://vercel.com/dashboard
echo 2. Test your app at your Vercel URL
echo 3. If there are errors, check logs: vercel logs YOUR-URL --tail
echo.
pause
