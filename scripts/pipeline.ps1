# scripts/pipeline.ps1 — Run the full ML pipeline
# Usage:
#   .\scripts\pipeline.ps1           # run all phases
#   .\scripts\pipeline.ps1 -Phase 2  # run a single phase
param(
    [ValidateRange(1,5)]
    [int]$Phase = 0   # 0 = all phases
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = ".\.venv\Scripts\python.exe"

function Run-Phase {
    param([int]$n, [string]$label, [string[]]$scripts)
    Write-Host "`n==> Phase $n — $label" -ForegroundColor Cyan
    foreach ($s in $scripts) {
        Write-Host "    python $s" -ForegroundColor Gray
        & $py $s
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    FAILED: $s (exit $LASTEXITCODE)" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
    Write-Host "    Phase $n done." -ForegroundColor Green
}

$phases = @{
    1 = @{ label = "Data Ingestion";          scripts = @(
        "src/ingestion/fetch_air_quality.py",
        "src/ingestion/fetch_weather.py",
        "src/ingestion/fetch_industrial.py",
        "src/ingestion/verify_data.py"
    )}
    2 = @{ label = "Data Cleaning";           scripts = @(
        "src/processing/clean_air_quality.py",
        "src/processing/clean_weather.py",
        "src/processing/clean_industrial.py",
        "src/processing/verify_cleaned.py"
    )}
    3 = @{ label = "Feature Engineering";     scripts = @(
        "src/features/build_features.py"
    )}
    4 = @{ label = "Model Training";          scripts = @(
        "src/models/baseline.py",
        "src/models/train_lgbm.py"
    )}
    5 = @{ label = "Evaluation + Interpret";  scripts = @(
        "src/models/evaluate.py",
        "src/models/interpret.py"
    )}
}

Write-Host "`nAir Quality Intelligence — Pipeline Runner" -ForegroundColor White

$toRun = if ($Phase -eq 0) { 1..5 } else { @($Phase) }

foreach ($n in $toRun) {
    $p = $phases[$n]
    Run-Phase -n $n -label $p.label -scripts $p.scripts
}

Write-Host "`nAll done." -ForegroundColor Green
