# local-llm-router quickstart — run from repo root or this folder
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not (Test-Path (Join-Path $Root "pyproject.toml"))) {
    throw "Could not find local-llm-router repo root (pyproject.toml)."
}

Set-Location $Root
Write-Host "Repo: $Root"
Write-Host ""

Write-Host ">> Installing local-llm-router with Ollama extras..."
pip install -e ".[ollama]" | Out-Null

Write-Host ">> Phase 0 — guided setup (consent + Ollama pulls)"
python -m local_llm_router setup --profile workstation_12gb --yes --config (Join-Path $PSScriptRoot "local-llm-router.models.json")
$env:LOCAL_LLM_ROUTER_MODELS_CONFIG = Join-Path $PSScriptRoot "local-llm-router.models.json"
Write-Host ""

Write-Host ">> Phase A — dry tour (no inference, instant)"
python (Join-Path $PSScriptRoot "mini_app.py") --tour
Write-Host ""

Write-Host ">> Phase B — CLI smoke"
python -m local_llm_router profiles
python -m local_llm_router benchmark --markdown --models qwen3:4b,qwen3:8b,qwen3:14b,qwen3:30b-a3b
Write-Host ""

$Live = $args -contains "--live"
if ($Live) {
    Write-Host ">> Phase C — live Ollama (one ask)"
    python (Join-Path $PSScriptRoot "mini_app.py") --tour --live
} else {
    Write-Host ">> Phase C skipped. Add --live to try_it.ps1 for one real generation."
    Write-Host "   Example: .\examples\quickstart\try_it.ps1 --live"
}
