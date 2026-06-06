# Reset pip + pytest caches so publish tests use THIS repo (local-llm-router), not legacy split-stack.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_pip-helpers.ps1")

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Legacy = Join-Path (Split-Path -Parent $Root) "split-stack"

Write-Host "Repo: $Root" -ForegroundColor Cyan

Uninstall-PipPackagesQuiet -Packages @("local-llm-router")

foreach ($dir in @($Root, $Legacy)) {
    if (-not (Test-Path $dir)) { continue }
    Write-Host "Clearing caches under $dir" -ForegroundColor DarkGray
    Get-ChildItem -Path $dir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $dir ".pytest_cache") -Recurse -Force -ErrorAction SilentlyContinue
}

if ((Test-Path $Legacy) -and ($Legacy -ne $Root)) {
    Write-Host ""
    Write-Host "WARNING: Legacy folder still exists:" -ForegroundColor Yellow
    Write-Host "  $Legacy"
    Write-Host "Rename or remove it if tests still fail."
    Write-Host ""
}

Set-Location $Root

Write-Host "Step 1/3: pip install -e .[dev] ..." -ForegroundColor Cyan
Invoke-Pip -PipArgumentList @("install", "-e", ".[dev]")
Assert-ExitCode -Code (Get-LastPythonExitCode) -Step "pip install"
Write-Host "Step 1/3: done." -ForegroundColor Green

Write-Host "Step 2/3: import local_llm_router ..." -ForegroundColor Cyan
Invoke-Python -PythonArgumentList @(
    "-c", "import local_llm_router; print('import OK', local_llm_router.__version__)"
)
Assert-ExitCode -Code (Get-LastPythonExitCode) -Step "import check"
Write-Host "Step 2/3: done." -ForegroundColor Green

Write-Host "Step 3/3: pytest ..." -ForegroundColor Cyan
Invoke-Python -PythonArgumentList @(
    "-m", "pytest", "-q", "--rootdir=$Root", "$Root\tests"
)
if ((Get-LastPythonExitCode) -ne 0) {
    Write-Error "pytest failed (exit $(Get-LastPythonExitCode))."
}
Write-Host "All steps passed." -ForegroundColor Green
exit 0
