# Visual browser demo

Local single-page demo for local-llm-router routing and the compare POC. **Demo only** — the product is the Python library.

## Run

```bash
cd local-llm-router
pip install -e ".[ollama]"
python examples/demo_ui/server.py
```

## Start (Windows)

From the local-llm-router repo:

```powershell
.\examples\demo_ui\start.ps1
```

Or manually:

```powershell
python examples/demo_ui/server.py --models-dir "$env:USERPROFILE\.ollama\models"
```

**Important:** If you already have a server on port 8765, stop it first (Ctrl+C in that terminal). An old server serves blank guide cards and empty disk inventory.

Open **http://127.0.0.1:8765** and hard-refresh (Ctrl+F5) so `app.js?v=7` loads.

**Page order (top → bottom):**

1. **Stack bar** — GPU VRAM + Gemma quant → recommended stack chips (resolved against your inventory)
2. **Try one prompt** — `route()` for a single prompt + hint
3. **Savings demo** — 5-step compare vs always-largest
4. **What model for what task** — tier ladder + hint→model table
5. **Installed models** — collapsed; disk/API inventory

**Stack bar:**

- **GPU VRAM** (8 / 12 / 16 / 24 / 32 GB) — maps to the same profiles as `local_llm_router.configure(vram_gb=...)`
- **Gemma quant** — `default`, `qat`, `qat_mobile`, or `bf16` (same as library `quant=` argument)
- **Recommended stack** — chips from the library preset; dashed chips are not found on disk/API
- **Custom stack** — optional comma-separated override for power users

Example for 16 GB + QAT: `gemma4:e4b`, `qwen3:8b`, `qwen3:14b`, plus `gemma4:26b-a4b` when QAT extras apply.

**Model source** dropdown:

- **API + disk manifests** — union of `/api/tags` and files under your Ollama model folder
- **Disk manifests only** — scans `OLLAMA_MODELS`, `~/.ollama/models`, and common dev paths
- **Ollama API only** — what the running server reports

If API shows 1 model but disk shows 10, Ollama is not pointed at your model folder. Set:

```powershell
$env:OLLAMA_MODELS = "$env:USERPROFILE\.ollama\models"
# restart Ollama service/app, then ollama list should show all tags
```

Or set `local_llm_router_OLLAMA_MODELS` to that path for disk scan only (dry compare works without fixing Ollama).

**Hints:** `lookup`, `explain`, `design`, `code`, `reason` — same as compare POC.

## What you see

1. **Compare POC** — 5 agent steps as cards; routed model vs always-largest baseline; tier colour badges
2. **Dry / Live toggle** — dry is instant; live calls Ollama and shows latency bars (needs models pulled)
3. **Try a prompt** — type text, optional hint, see tier + model
4. **Ollama models** — collapsed inventory from disk manifests and `/api/tags`

## API (same process as UI)

| Endpoint | Purpose |
| --- | --- |
| `GET /api/stack?vram_gb=16&quant=qat&source=both` | Recommended stack + resolved models |
| `GET /api/stack-options` | VRAM and quant dropdown values |
| `GET /api/guide?vram_gb=16&quant=qat&source=both` | Tier ladder + hint routes |
| `GET /api/compare?vram_gb=16&quant=qat&live=0` | Dry compare JSON |
| `GET /api/compare?...&live=1` | Live compare (502 + error if Ollama fails) |
| `POST /api/route` | `{prompt, vram_gb?, quant?, source?, models?, hint?}` |

CLI equivalent: `stack compare` — see [`../poc_compare/README.md`](../poc_compare/README.md).

## Options

```bash
python examples/demo_ui/server.py --port 8765 --base-url http://127.0.0.1:11434
```

## Related backlog

Local model freshness / staleness checks are tracked in [`../../docs/BACKLOG.md`](../../docs/BACKLOG.md) — not part of this demo yet.
