# scripts/setup.ps1 — One-time project setup
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host "`n[1/3] Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

Write-Host "`n[2/3] Installing dependencies..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\pip.exe install -r requirements.txt --quiet
Write-Host "      Done." -ForegroundColor Green

Write-Host "`n[3/3] Checking .env file..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "      Created .env from .env.example" -ForegroundColor Yellow
    Write-Host "      >> Open .env and set your OPENAQ_API_KEY" -ForegroundColor Yellow
} else {
    Write-Host "      .env already exists." -ForegroundColor Green
}

Write-Host "`nSetup complete. Next steps:" -ForegroundColor Green
Write-Host "  Run pipeline : .\scripts\pipeline.ps1"
Write-Host "  Run app      : .\scripts\app.ps1`n"
