# Installs this project's packages into the main Python 3.12 interpreter (no virtual environment)
# without changing any package that interpreter already has.
#
# Run from the project folder:
#   powershell -ExecutionPolicy Bypass -File .\setup_local_env.ps1
#
# What it does:
#   1. Saves the interpreter's current package list to local_env_before.txt (for comparison or rollback).
#   2. Installs requirements-dev.txt at the versions in requirements-lock.txt, except that any package
#      already installed is held at its current version. If that is impossible, pip stops and nothing changes.
#   3. Installs this project in editable mode, points the pre-commit hook at this interpreter, and runs the tests.

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Start-Transcript -Path (Join-Path $PSScriptRoot 'local_env_setup.log') -Force | Out-Null

function Invoke-Py {
    & py -3.12 @args | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Command failed: py -3.12 $($args -join ' ')" }
}
function Get-Key([string]$name) { ($name -replace '[-_.]+', '-').ToLower() }

Invoke-Py --version

# 1. Snapshot
$before = & py -3.12 -m pip freeze --all
$before | Set-Content -Encoding utf8 local_env_before.txt
$existing = @{}
foreach ($line in $before) {
    if ($line -match '^([A-Za-z0-9_.\-]+)==') { $existing[(Get-Key $Matches[1])] = $line }
}
Write-Host "Packages already installed: $($existing.Count)"

# 2. Constraints: lock-file versions for new packages, current versions for existing ones
$constraints = New-Object System.Collections.Generic.List[string]
foreach ($line in Get-Content requirements-lock.txt) {
    if ($line -match '^([A-Za-z0-9_.\-]+)==' -and -not $existing.ContainsKey((Get-Key $Matches[1]))) {
        $constraints.Add($line)
    }
}
foreach ($line in $existing.Values) { if ($line -notmatch '^pip==') { $constraints.Add($line) } }
$constraintFile = Join-Path $env:TEMP 'valuation_monitor_constraints.txt'
$constraints | Set-Content -Encoding ascii $constraintFile

Invoke-Py -m pip install -r requirements-dev.txt -c $constraintFile
Invoke-Py -m pip install -e . --no-deps

# Confirm nothing that was already installed has changed
$after = & py -3.12 -m pip freeze --all
$changed = $before | Where-Object { $_ -match '==' -and $after -notcontains $_ }
if ($changed) {
    Write-Warning "These existing packages changed (originals are in local_env_before.txt):"
    $changed | ForEach-Object { Write-Warning "  $_" }
} else {
    Write-Host "All $($existing.Count) previously installed packages are unchanged."
}
Invoke-Py -m pip check

# 3. Pre-commit hook and tests
Invoke-Py -m pre_commit install
Invoke-Py -c "import valuation_monitor, duckdb, splink, lightgbm, catboost, mapie, shap, mlflow, streamlit; print('Imports OK')"
Invoke-Py -m pytest -q
Write-Host "Done. Use 'py -3.12 -m ...' for project commands (see README)."
Stop-Transcript | Out-Null
