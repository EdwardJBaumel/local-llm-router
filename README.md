# local-llm-router

**A Python routing library for local LLM agent loops.**

Give local-llm-router a prompt and your model list. It returns a complexity tier and which model to call. You keep your agent runner, gateway, or Ollama client — local-llm-router only decides *which* local model each step should use.

Zero runtime dependencies. Works offline. No inference, no agent framework, no chat UI.

## Install

```bash
pip install local-llm-router
pip install "local-llm-router[ollama]"   # optional: Ollama discovery, llm-router ask
```

## Quick start

```python
import local_llm_router

local_llm_router.configure(vram_gb=16, quant="qat")  # once — or local_llm_router_VRAM_GB=16

for step in agent_steps:
    tier, model = local_llm_router.route(step.prompt, hint=step.hint)
    response = your_llm.complete(model=model, prompt=step.prompt)
```

Power-user path (explicit tier map):

```python
from local_llm_router import assign_tiers, route_prompt

tiers = assign_tiers(["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
tier, model = route_prompt(step.prompt, tiers, hint=step.hint)
```

Check your stack before routing:

```bash
llm-router doctor --check-stack --vram-gb 16 --quant qat
```

**Integration guide:** [`docs/for-app-authors.md`](docs/for-app-authors.md) · [`docs/integration.md`](docs/integration.md)

## What it does

| Piece | Role |
| --- | --- |
| **`configure(vram_gb=..., quant=...)`** | Set GPU budget + Gemma quant assumption once |
| **`route(prompt, hint=...)`** | Pick `(tier, model_name)` for one agent step |
| **`assign_tiers` / `route_prompt`** | Same routing with your own tier map |
| **`llm-router compare` / `stack benchmark`** | CLI evidence — dry by default |

Step hints: `lookup`, `explain`, `design`, `code`, `reason` — override keyword scoring when you know the agent phase.

## VRAM and quant

```python
local_llm_router.configure(vram_gb=16, quant="qat")
```

| VRAM | Profile |
| --- | --- |
| ≤8 / 12 / 16 / 24 / 32 GB | `workstation_8gb` … `workstation_32gb` |

`quant=` is **not** per-prompt routing — it tells local-llm-router which pull format you use so VRAM filters and stack suggestions stay honest (QAT vs default Ollama Q4). Details: [`docs/local-models.md`](docs/local-models.md).

## What it is not

Routing primitives only — not a chat app, agent framework, or multi-cloud proxy. Optional browser demo and VS Code panel are examples, not the product.

## Examples (optional)

Clone the repo only if you want demos or to contribute:

| Example | Command |
| --- | --- |
| Agent runner | `python examples/agent_runner/run.py` |
| Compare POC | `llm-router compare` |
| Browser demo | `python examples/demo_ui/server.py` → http://127.0.0.1:8765 |
| Quickstart tour | `examples/quickstart/try_it.ps1` |

See `examples/*/README.md` for each.

## Contributors

```bash
git clone https://github.com/edwardjbaumel/local-llm-router.git
cd local-llm-router
pip install -e ".[dev,ollama]"
pytest
llm-router setup --profile 12gb --dry-run
```

Docs: [`docs/publishing.md`](docs/publishing.md) · [`docs/security.md`](docs/security.md) · [`docs/backlog.md`](docs/backlog.md)

## Related

[Local Recruiting Ops](https://github.com/edwardjbaumel/local-recruiting-ops) — separate project by the same author; local-llm-router does not depend on it.
