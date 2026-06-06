# Interactive PyPI upload — prompts for token so you don't fight PowerShell quoting.
# Usage:
#   .\scripts\upload-pypi.ps1              # real PyPI (pypi.org token)
#   .\scripts\upload-pypi.ps1 -TestPyPI    # test.pypi.org token

param(
    [switch]$TestPyPI,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if ($TestPyPI) {
    $repoName = "TestPyPI"
    $repoFlag = @("--repository", "testpypi")
    $tokenHint = "Paste token from https://test.pypi.org/manage/account/token/"
} else {
    $repoName = "PyPI"
    $repoFlag = @()
    $tokenHint = "Paste token from https://pypi.org/manage/account/token/"
}

Write-Host ""
Write-Host "=== Upload to $repoName ===" -ForegroundColor Cyan
Write-Host $tokenHint
Write-Host "Username is always the literal text: __token__" -ForegroundColor DarkGray
Write-Host ""

$token = Read-Host "Paste API token (hidden)" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)
)
if (-not $plain -or -not $plain.StartsWith("pypi-")) {
    Write-Error "That doesn't look like a PyPI token (should start with pypi-)."
}

$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $plain

if (-not $SkipBuild) {
    Write-Host "Building package..." -ForegroundColor Cyan
    python -m pytest -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
    python -m build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    twine check dist/*
} elseif (-not (Test-Path "dist")) {
    Write-Error "No dist/ folder. Run without -SkipBuild first."
}

Write-Host "Uploading to $repoName..." -ForegroundColor Cyan
& twine upload @repoFlag dist/*

Write-Host ""
Write-Host "Success on $repoName." -ForegroundColor Green
if ($TestPyPI) {
    Write-Host "Verify: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ local-llm-router"
} else {
    Write-Host "Verify: pip install local-llm-router"
}

# Clear token from this session
Remove-Item Env:TWINE_PASSWORD -ErrorAction SilentlyContinue
