#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "Repo: $ROOT"
echo ""

echo ">> Installing local-llm-router with Ollama extras..."
pip install -e ".[ollama]" >/dev/null

CONFIG="$(cd "$(dirname "$0")" && pwd)/local-llm-router.models.json"
export LOCAL_LLM_ROUTER_MODELS_CONFIG="$CONFIG"

echo ">> Phase 0 — guided setup (consent + Ollama pulls)"
python -m local_llm_router setup --profile workstation_12gb --yes --config "$CONFIG"
echo ""

echo ">> Phase A — dry tour (no inference, instant)"
python examples/quickstart/mini_app.py --tour
echo ""

echo ">> Phase B — CLI smoke"
python -m local_llm_router profiles
python -m local_llm_router benchmark --markdown --models qwen3:4b,qwen3:8b,qwen3:14b,qwen3:30b-a3b
echo ""

if [[ "${1:-}" == "--live" ]]; then
  echo ">> Phase C — live Ollama (one ask)"
  python examples/quickstart/mini_app.py --tour --live
else
  echo ">> Phase C skipped. Re-run with --live for one real generation."
  echo "   Example: ./examples/quickstart/try_it.sh --live"
fi
