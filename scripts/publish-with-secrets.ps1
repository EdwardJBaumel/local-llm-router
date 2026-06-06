# Publish using token from gitignored scripts/publish-secrets.ps1
#
# Setup (once):
#   Copy-Item .\scripts\publish-secrets.ps1.example .\scripts\publish-secrets.ps1
#   notepad .\scripts\publish-secrets.ps1   # paste pypi-... token
#
# Usage:
#   .\scripts\publish-with-secrets.ps1              # PyPI
#   .\scripts\publish-with-secrets.ps1 -TestPyPI    # TestPyPI first

param(
    [switch]$TestPyPI,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Scripts = Split-Path -Parent $MyInvocation.MyCommand.Path
$Secrets = Join-Path $Scripts "publish-secrets.ps1"

if (-not (Test-Path $Secrets)) {
    Write-Error @"
Missing $Secrets

Copy the example and add your token:

  Copy-Item .\scripts\publish-secrets.ps1.example .\scripts\publish-secrets.ps1
  notepad .\scripts\publish-secrets.ps1
"@
}

. $Secrets

$token = if ($TestPyPI -and $TestPyPIToken) { $TestPyPIToken } else { $PyPIToken }
$token = "$token".Trim()
if (-not $token -or $token -match "PASTE-YOUR-TOKEN") {
    Write-Error "Set a real pypi- token in publish-secrets.ps1"
}

$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $token

try {
    $upload = Join-Path $Scripts "upload-pypi.ps1"
    $args = @()
    if ($TestPyPI) { $args += "-TestPyPI" }
    if ($SkipBuild) { $args += "-SkipBuild" }
    & $upload @args
} finally {
    Remove-Item Env:TWINE_PASSWORD -ErrorAction SilentlyContinue
}
