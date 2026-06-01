#!/usr/bin/env powershell
# Prarambha Vercel Production Deployment Script
# This script commits and pushes all changes to GitHub and deploys to Vercel

Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "  Prarambha - Production Deployment Script" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""

# Check if git is installed
try {
    git --version | Out-Null
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git: https://git-scm.com/download/win"
    exit 1
}

# Check if we're in a git repository
try {
    git rev-parse --git-dir | Out-Null
} catch {
    Write-Host "ERROR: Not a git repository" -ForegroundColor Red
    Write-Host "Please run: git init"
    exit 1
}

# Display current status
Write-Host "Current Git Status:" -ForegroundColor Cyan
Write-Host ""
git status --short
Write-Host ""

# Confirm before proceeding
$confirm = Read-Host "Continue with deployment? (yes/no)"
if ($confirm -ne "yes" -and $confirm -ne "y") {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Step 1: Adding all files..." -ForegroundColor Cyan
git add -A
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to add files" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Files staged" -ForegroundColor Green

Write-Host ""
Write-Host "Step 2: Creating commit..." -ForegroundColor Cyan
git commit -m "Production deployment: Fix Vercel 500 errors, add comprehensive error handling, optimize database operations"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create commit" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Commit created" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Pushing to GitHub..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Push to main failed. Trying master branch..." -ForegroundColor Yellow
    git push origin master
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to push changes" -ForegroundColor Red
        Write-Host "Please verify your git configuration and try again"
        exit 1
    }
}
Write-Host "✓ Changes pushed to GitHub" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Deploying to Vercel..." -ForegroundColor Cyan
vercel --prod
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Vercel deployment command failed" -ForegroundColor Yellow
    Write-Host "Please deploy manually:"
    Write-Host "  - Go to https://vercel.com"
    Write-Host "  - Select your project"
    Write-Host "  - Deploy from git"
}

Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "  ✓ Deployment Process Complete!" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Check Vercel deployment status at: https://vercel.com/dashboard"
Write-Host "2. Test your app at your Vercel URL"
Write-Host "3. If there are errors, check logs: vercel logs YOUR-URL --tail"
Write-Host ""
Read-Host "Press Enter to exit"
