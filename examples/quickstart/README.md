# Quickstart — feel the setup before you ship

15-minute hands-on tour: config profile → tier map → routing → benchmark → optional Ollama.

## Prerequisites

- Python 3.10+
- Optional for live generation: [Ollama](https://ollama.com) running locally
- Optional models to pull (match the default ladder):

```bash
ollama pull qwen3:4b
ollama pull qwen3:8b
ollama pull qwen3:14b
ollama pull qwen3:30b-a3b
```

You can use fewer models; edit `local-llm-router.models.json` or pass `--models` on the CLI.

**Not a Qwen shop.** Gemma, Llama, Phi, DeepSeek, Codellama and custom tags work the same way — see [`../../docs/local-models.md`](../../docs/local-models.md) for family notes and example ladders per VRAM preset.

Alternative pulls worth trying:

```bash
ollama pull gemma3:4b
ollama pull phi3:mini
ollama pull llama3.2:3b
# then pass --models gemma3:4b,phi3:mini,qwen3:14b
```

## One-command tour (Windows)

From repo root:

```powershell
.\examples\quickstart\try_it.ps1
```

With one live Ollama call at the end:

```powershell
.\examples\quickstart\try_it.ps1 --live
```

Linux/macOS:

```bash
chmod +x examples/quickstart/try_it.sh
./examples/quickstart/try_it.sh
./examples/quickstart/try_it.sh --live
```

## Manual walkthrough

### 1. Install

```bash
cd local-llm-router
pip install -e ".[ollama]"
llm-router setup --profile workstation_12gb
```

`llm-router setup` asks which preset to use (if omitted), shows missing models, **asks consent before download**, then writes `local-llm-router.models.json`.

Non-interactive:

```bash
llm-router setup --profile 12gb --yes
```

### 2. Point at the example config

```powershell
# PowerShell
$env:LOCAL_LLM_ROUTER_MODELS_CONFIG = "examples\quickstart\local-llm-router.models.json"
```

```bash
# bash
export LOCAL_LLM_ROUTER_MODELS_CONFIG=examples/quickstart/local-llm-router.models.json
```

Edit `deployment_profile` in that file to match your GPU:

| Your GPU | Set to |
| --- | --- |
| 8 GB class | `workstation_8gb` |
| 12 GB (default) | `workstation_12gb` |
| 16 GB | `workstation_16gb` |
| 4090 / 3090 | `workstation_24gb` |
| 5090 | `workstation_32gb` |
| Private fleet / dual GPU | `datacenter` + custom `models[]` |

### 3. Run the tour (dry — no inference)

```bash
python examples/quickstart/mini_app.py --tour
```

You should see: profile line → tier map → four routed prompts → benchmark table.

### 4. Try a profile override without editing config

```bash
python examples/quickstart/mini_app.py --tour --profile 32gb
llm-router models --profile 24gb
```

### 5. CLI equivalents

```bash
llm-router profiles
llm-router doctor
llm-router route --prompt "what is caching?" --json --models qwen3:4b,qwen3:8b,qwen3:14b
stack benchmark --markdown
llm-router ask --prompt "what is caching?" --json --models qwen3:4b,qwen3:8b,qwen3:14b
```

### 6. Live generation

```bash
python examples/quickstart/mini_app.py --tour --live
```

Or route one prompt from Python:

```bash
python examples/quickstart/mini_app.py --prompt "design webhook retries"
```

## What you are testing

```text
local-llm-router.models.json  →  deployment_profile + model weights
        ↓
assign_tiers(models)     →  simple / medium / complex / reasoning slots
        ↓
route_prompt(text, tiers) →  pick model name (no network)
        ↓
your Ollama / gateway     →  generate text
```

This example keeps config in `examples/quickstart/` so you do not touch your home directory until you are ready to ship your own `local-llm-router.models.json`.

## Copy into your own project

When satisfied:

1. Copy `local-llm-router.models.json` to your app repo root (or `~/.config/local-llm-router/models.json`).
2. Copy the integration snippet from [`../agent_runner/run.py`](../agent_runner/run.py).
3. See [`../../docs/integrations/litellm.md`](../../docs/integrations/litellm.md) for gateway wiring.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `No models available` | Start Ollama; pull at least two models; check `--models` list |
| Fewer than two models after filter | Raise profile (`--profile 16gb`) or use `datacenter` |
| `requests` missing | `pip install -e ".[ollama]"` |
| Windows emoji garble on `llm-router ask` | Use `--json` or `$env:PYTHONIOENCODING="utf-8"` |
