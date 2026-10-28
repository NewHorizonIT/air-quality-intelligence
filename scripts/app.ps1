# scripts/app.ps1 — Launch the Streamlit app
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host "`nStarting Air Quality Intelligence app..." -ForegroundColor Cyan
Write-Host "  URL: http://localhost:8501`n" -ForegroundColor White

& .\.venv\Scripts\python.exe -m streamlit run app/main.py
