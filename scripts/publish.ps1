# Publish split-stack to TestPyPI and/or PyPI.
# Requires API tokens as env vars (never commit tokens).
#
# TestPyPI:
#   $env:TWINE_USERNAME = "__token__"
#   $env:TWINE_PASSWORD = "<testpypi-api-token>"
#   .\scripts\publish.ps1 -Target TestPyPI
#
# Production PyPI (use a separate token scoped to split-stack):
#   $env:TWINE_PASSWORD = "<pypi-api-token>"
#   .\scripts\publish.ps1 -Target PyPI
#
# Full flow (TestPyPI smoke test, then PyPI):
#   .\scripts\publish.ps1 -Target All

param(
    [ValidateSet("TestPyPI", "PyPI", "All")]
    [string]$Target = "TestPyPI",
    [switch]$SkipBuild,
    [switch]$SkipSmokeTest,
    [switch]$SkipGitTag
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not $env:TWINE_USERNAME) {
    $env:TWINE_USERNAME = "__token__"
}

function Require-Token {
    if (-not $env:TWINE_PASSWORD) {
        Write-Error @"
TWINE_PASSWORD is not set.

Easiest fix — run the interactive uploader (no quoting headaches):

  .\scripts\upload-pypi.ps1 -TestPyPI
  .\scripts\upload-pypi.ps1

Or set env vars — QUOTES ARE REQUIRED in PowerShell:

  `$env:TWINE_USERNAME = "__token__"
  `$env:TWINE_PASSWORD = "pypi-paste-full-token-here"

Wrong (will fail):
  `$env:TWINE_USERNAME = __token__
  `$env:TWINE_PASSWORD = pypi-...
"@
    }
    if (-not $env:TWINE_USERNAME) {
        $env:TWINE_USERNAME = "__token__"
    }
}

function Invoke-Build {
    if ($SkipBuild) { return }
    Write-Host "==> pytest" -ForegroundColor Cyan
    python -m pytest -q
    Write-Host "==> clean + build" -ForegroundColor Cyan
    foreach ($dir in @("dist", "build")) {
        if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
    }
    Get-ChildItem -Filter "*.egg-info" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    python -m build
    twine check dist/*
}

function Upload-TestPyPI {
    Require-Token
    Write-Host "==> upload TestPyPI" -ForegroundColor Cyan
    twine upload --repository testpypi dist/*
}

function Smoke-Test-TestPyPI {
    if ($SkipSmokeTest) { return }
    Write-Host "==> smoke test from TestPyPI" -ForegroundColor Cyan
    $venv = Join-Path $env:TEMP "split-stack-smoke-venv"
    if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
    python -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install -q --upgrade pip
    & "$venv\Scripts\pip.exe" install -q `
        --index-url https://test.pypi.org/simple/ `
        --extra-index-url https://pypi.org/simple/ `
        "split-stack==0.2.0"
    & "$venv\Scripts\python.exe" -c "import split_stack; print('version', split_stack.__version__)"
    & "$venv\Scripts\stack.exe" route --prompt "what is JWT?" --hint lookup --json `
        --models gemma4:e4b,qwen3:8b,qwen3:14b
    Write-Host "Smoke test OK" -ForegroundColor Green
}

function Upload-PyPI {
    Require-Token
    Write-Host "==> upload PyPI" -ForegroundColor Cyan
    twine upload dist/*
}

function Invoke-GitTag {
    if ($SkipGitTag) { return }
    $tag = "v0.2.0"
    Write-Host "==> git tag $tag (if missing) and push" -ForegroundColor Cyan
    git fetch origin 2>$null
    $exists = git tag -l $tag
    if (-not $exists) {
        git tag -a $tag -m "Release split-stack 0.2.0"
    }
    git push origin main
    git push origin $tag
}

Invoke-Build

switch ($Target) {
    "TestPyPI" {
        Upload-TestPyPI
        Smoke-Test-TestPyPI
    }
    "PyPI" {
        Upload-PyPI
        Invoke-GitTag
    }
    "All" {
        Upload-TestPyPI
        Smoke-Test-TestPyPI
        Write-Host "TestPyPI OK. Set production TWINE_PASSWORD if different, then re-run with -Target PyPI" -ForegroundColor Yellow
        Upload-PyPI
        Invoke-GitTag
    }
}

Write-Host "Done ($Target)." -ForegroundColor Green
