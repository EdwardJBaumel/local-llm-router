# Publish local-llm-router to TestPyPI and/or PyPI.
# Requires API tokens as env vars (never commit tokens).
#
# TestPyPI:
#   $env:TWINE_USERNAME = "__token__"
#   $env:TWINE_PASSWORD = "<testpypi-api-token>"
#   .\scripts\publish.ps1 -Target TestPyPI
#
# Production PyPI (use a separate token scoped to local-llm-router):
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
$Scripts = Join-Path $Root "scripts"
. (Join-Path $Scripts "_pip-helpers.ps1")
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
    & (Join-Path $Scripts "fix-publish-env.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
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
    $venv = Join-Path $env:TEMP "local-llm-router-smoke-venv"
    if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
    python -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install -q --upgrade pip
    $version = (python -c "import pathlib,re; m=re.search(r'^version = \"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text(encoding='utf-8'), re.M); print(m.group(1) if m else '0.0.0')").Trim()
    & "$venv\Scripts\pip.exe" install -q `
        --index-url https://test.pypi.org/simple/ `
        --extra-index-url https://pypi.org/simple/ `
        "local-llm-router==$version"
    & "$venv\Scripts\python.exe" -c "import local_llm_router; print('version', local_llm_router.__version__)"
    & "$venv\Scripts\llm-router.exe" route --prompt "what is JWT?" --mode chat --json `
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
    $version = (python -c "import pathlib,re; m=re.search(r'^version = \"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text(encoding='utf-8'), re.M); print(m.group(1) if m else '0.0.0')").Trim()
    $tag = "v$version"
    Write-Host "==> git tag $tag (if missing) and push" -ForegroundColor Cyan
    git fetch origin 2>$null
    $exists = git tag -l $tag
    if (-not $exists) {
        git tag -a $tag -m "Release local-llm-router $version"
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
