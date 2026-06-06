# Visual browser demo

Local single-page demo for split-stack routing and the compare POC. **Demo only** — the product is the Python library.

## Run

```bash
cd split-stack
pip install -e ".[ollama]"
python examples/demo_ui/server.py
```

## Start (Windows)

From the split-stack repo:

```powershell
.\examples\demo_ui\start.ps1
```

Or manually:

```powershell
python examples/demo_ui/server.py --models-dir "$env:USERPROFILE\.ollama\models"
```

**Important:** If you already have a server on port 8765, stop it first (Ctrl+C in that terminal). An old server serves blank guide cards and empty disk inventory.

Open **http://127.0.0.1:8765** and hard-refresh (Ctrl+F5) so `app.js?v=3` loads.

**Model guide** (top section) shows:
- Tier ladder for your active stack (simple / medium / complex / reasoning)
- Each agent hint (`lookup`, `explain`, `design`, `code`, `reason`) and which model `route_prompt` picks
- Cards for every model on disk — what it is best for, whether it is in the compare stack

**Model source** dropdown:
- **API + disk manifests** — union of `/api/tags` and files under your Ollama model folder
- **Disk manifests only** — scans `OLLAMA_MODELS`, `~/.ollama/models`, and `~/dev/Tools/.ollama/models`
- **Ollama API only** — what the running server reports

If API shows 1 model but disk shows 10, Ollama is not pointed at your model folder. Set:

```powershell
$env:OLLAMA_MODELS = "$env:USERPROFILE\.ollama\models"
# restart Ollama service/app, then ollama list should show all tags
```

Or set `SPLIT_STACK_OLLAMA_MODELS` to that path for disk scan only (dry compare works without fixing Ollama).

**Stack presets:** default **From your Ollama (auto ladder)** picks small/mid/large from your inventory. **Mixed 12 GB** uses `gemma4:e4b,qwen3:8b,qwen3:14b`.

**Hints:** `lookup`, `explain`, `design`, `code`, `reason` — same as compare POC.

Windows shortcut:

```powershell
.\examples\demo_ui\start.ps1
```

## What you see

1. **Compare POC** — 5 agent steps as cards; routed model vs always-largest baseline; tier colour badges
2. **Dry / Live toggle** — dry is instant; live calls Ollama and shows latency bars (needs models pulled)
3. **Try a prompt** — type text, optional hint, see tier + model
4. **Ollama models** — sidebar list from `/api/tags`

## API (same process as UI)

| Endpoint | Purpose |
| --- | --- |
| `GET /api/compare?models=...&live=0` | Dry compare JSON |
| `GET /api/compare?models=...&live=1` | Live compare (502 + error if Ollama fails) |
| `POST /api/route` | `{prompt, models, hint?}` |
| `GET /api/models` | Installed Ollama tags |

CLI equivalent: `stack compare` — see [`../poc_compare/README.md`](../poc_compare/README.md).

## Options

```bash
python examples/demo_ui/server.py --port 8765 --base-url http://127.0.0.1:11434
```
