# Start split-stack demo UI with your Ollama models folder.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Project = Split-Path -Parent (Split-Path -Parent $Root)

$ModelsDir = $env:SPLIT_STACK_OLLAMA_MODELS
if (-not $ModelsDir) {
    $ModelsDir = $env:OLLAMA_MODELS
}
$HomeModels = Join-Path $env:USERPROFILE ".ollama\models"
$ToolsModels = Join-Path $env:USERPROFILE "dev\Tools\.ollama\models"
if (-not $ModelsDir) {
    if (Test-Path $HomeModels) { $ModelsDir = $HomeModels }
    elseif (Test-Path $ToolsModels) { $ModelsDir = $ToolsModels }
}

$ServerArgs = @("--port", "8765")
if (Test-Path $ModelsDir) {
    $env:SPLIT_STACK_OLLAMA_MODELS = $ModelsDir
    $ServerArgs += @("--models-dir", $ModelsDir)
    Write-Host "Models dir: $ModelsDir"
} else {
    Write-Warning "Models dir not found at $ModelsDir - set SPLIT_STACK_OLLAMA_MODELS"
}

Set-Location $Project
python (Join-Path $Root "server.py") @ServerArgs
