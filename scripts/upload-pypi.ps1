# Interactive PyPI upload — prompts for token so you don't fight PowerShell quoting.
# Usage:
#   .\scripts\upload-pypi.ps1              # real PyPI (pypi.org token)
#   .\scripts\upload-pypi.ps1 -TestPyPI    # test.pypi.org token

param(
    [switch]$TestPyPI,
    [switch]$SkipBuild,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Scripts = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Scripts
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

if ($env:TWINE_PASSWORD) {
    Write-Host "Using TWINE_PASSWORD from environment." -ForegroundColor DarkGray
    $plain = $env:TWINE_PASSWORD.Trim()
} else {
    Write-Host $tokenHint
    Write-Host "Username is always the literal text: __token__" -ForegroundColor DarkGray
    Write-Host ""
    $token = Read-Host "Paste API token (hidden)" -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)
    ).Trim()
}
if (-not $plain -or -not $plain.StartsWith("pypi-")) {
    Write-Error "That doesn't look like a PyPI token (should start with pypi-)."
}
if ($plain.Length -lt 80) {
    Write-Warning "Token looks short (${plain.Length} chars). Paste the full token from PyPI (usually 180+ chars)."
}

$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $plain

if (-not $SkipBuild) {
    Write-Host "Building package..." -ForegroundColor Cyan
    if (-not $SkipTests) {
        $fix = Join-Path $Scripts "fix-publish-env.ps1"
        & $fix
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "Skipping tests (-SkipTests)" -ForegroundColor Yellow
    }
    Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
    python -m build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    twine check dist/*
} elseif (-not (Test-Path "dist")) {
    Write-Error "No dist/ folder. Run without -SkipBuild first."
}

Write-Host "Uploading to $repoName..." -ForegroundColor Cyan
& twine upload @repoFlag dist/*
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Upload failed. Common 403 Forbidden fixes:" -ForegroundColor Yellow
    Write-Host "  1. Enable 2FA on your PyPI account (required for uploads)"
    Write-Host "  2. Create a NEW API token at $tokenHint"
    Write-Host "  3. Scope: Entire account (first publish) or project local-llm-router"
    Write-Host "  4. Use a $repoName token here - not TestPyPI if uploading to pypi.org"
    Write-Host "  5. Username must be exactly: __token__ (twine sets this for you)"
    Write-Host "  6. Paste once, no spaces; token should be ~180+ characters"
    Write-Host ""
    Write-Host "Retry with verbose output:" -ForegroundColor Cyan
    Write-Host '  twine upload --verbose dist/*'
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Success on $repoName." -ForegroundColor Green
if ($TestPyPI) {
    Write-Host "Verify: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ local-llm-router"
} else {
    Write-Host "Verify: pip install local-llm-router"
}

# Clear token from this session
Remove-Item Env:TWINE_PASSWORD -ErrorAction SilentlyContinue
