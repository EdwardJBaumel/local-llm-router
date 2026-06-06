# Local models — what split-stack knows and what to add

split-stack routes by **model name + weight**, not by provider API. If Ollama (or your gateway) can serve it, you can tier it.

## Three layers (how names get ranked)

| Layer | When it runs | What it does |
| --- | --- | --- |
| **Built-in registry** | Default, no config file | Substring matches for common Ollama tags (`qwen3:8b`, `gemma4:e4b`, …) |
| **Your config** | `split-stack.models.json` | Overrides/extends built-in rows; set `deployment_profile` |
| **Heuristics** | Unknown tag | Parses `:4b`, `:14b`, `:e4b`, `:30b-a3b` patterns; guesses family from name |

You do **not** need a registry row for every pull. Heuristics cover most `family:size` tags well enough for tier ordering. Add explicit rows when:

- The tag does not encode size (`my-company-fast-v2`)
- MoE or quant suffixes confuse ranking (`30b-a3b` vs dense `30b`)
- VRAM filter should treat a model differently from the default guess

## Built-in families (v0.2)

| Family | Example tags | Typical ladder role |
| --- | --- | --- |
| **Qwen3** | `qwen3:4b`, `8b`, `14b`, `30b`, `30b-a3b` | Default demo stack; MoE `30b-a3b` = big tier without 30b VRAM |
| **Gemma** | `gemma3:4b`, `gemma3:12b`, `gemma4:e4b`, `:e2b` | Strong small models; `e4b` / efficiency variants |
| **Llama** | `llama3.2:1b`, `3b`, `llama3.1:8b`, `70b` | Meta ecosystem; 1b/3b for simple tier |
| **Mistral** | `mistral:7b`, `mistral-nemo` | Mid-size general models |
| **Phi** | `phi3:mini`, `phi4`, `phi4-reasoning` | Microsoft; good on 8–12 GB laptops |
| **DeepSeek** | `deepseek-r1`, `deepseek-coder-v2` | Reasoning/code; map reasoning tier carefully |
| **Code** | `codellama`, `starcoder2`, `qwen2.5-coder` | Agent code steps; often medium/complex only |

Run `stack models` to see how **your** installed tags resolve (`registry` vs `heuristic` column).

## Suggested stacks by VRAM preset

Canonical **mixed specialist** stacks ship in code (`stack stacks`). Philosophy: **Gemma min, Qwen spine, coder on code, R1/MoE on reasoning**. Beyond 32 GB → custom config or `datacenter`.

| Profile | Models to pull | Tier assignment |
| --- | --- | --- |
| **8 GB** | `gemma4:e4b`, `qwen3:8b` | flat: Gemma simple, Qwen8 everything else |
| **12 GB** | `gemma4:e4b`, `qwen3:8b`, `qwen3:14b`, `deepseek-r1:8b` | Gemma lookup / Qwen8 medium / Qwen14 complex / R1 reason |
| **16 GB** | above + `phi4`, `deepseek-coder:6.7b` | adds code slot for refactor/debug prompts |
| **24 GB** | Gemma + Qwen8/14 + `qwen3:30b-a3b` + coder | MoE top for complex/reasoning fallback |
| **32 GB** | 24 GB stack + `deepseek-r1:8b` | separate reasoning + code specialists |

```bash
stack stacks
stack stacks --profile workstation_24gb --json
```

### Routing logic (v0.2)

1. **Agent hint** (`lookup`, `explain`, `design`, `code`, `reason`) overrides text heuristics when your loop knows the step type.
2. **Text heuristics** score prompt complexity when no hint is passed.
3. **Code slot** — refactor/debug/` ``` ` prompts on COMPLEX/MEDIUM use `tiers.code` when configured.

```python
from split_stack import assign_recommended_tiers, route_prompt

tiers = assign_recommended_tiers("workstation_16gb")
route_prompt("what is caching?", tiers, hint="lookup")          # gemma4:e4b
route_prompt("refactor auth for tests", tiers)                   # deepseek-coder if in stack
route_prompt("prove policy step by step", tiers, hint="reason")  # deepseek-r1
```

CLI:

```bash
stack route --prompt "refactor auth module" --hint code --models gemma4:e4b,qwen3:14b,deepseek-coder:6.7b
```

These are **starting points**, not requirements. One family end-to-end is fine.

### 8 GB (`workstation_8gb`)

```text
simple:   llama3.2:3b | gemma3:4b | qwen3:4b
medium:   mistral:7b | qwen3:8b
complex:  qwen3:8b (same as medium — flat ladder is OK)
```

### 12 GB default (`workstation_12gb`)

```text
simple:   qwen3:4b | gemma4:e4b
medium:   qwen3:8b | phi3:mini
complex:  qwen3:14b | gemma3:12b
reasoning: qwen3:14b | deepseek-r1:8b
```

### 24 GB (`workstation_24gb`)

```text
simple → medium → complex → reasoning
qwen3:4b → qwen3:8b → qwen3:14b → qwen3:30b-a3b
```

### 32 GB (`workstation_32gb`)

Same ladder; room for higher quants or `gemma3:27b`-class models if you add them to config.

### Apple Silicon (unified memory)

Steam-style GPU VRAM presets do not apply literally. Pick the preset closest to the **memory you devote to models** (often 16–24 GB effective on a 32–64 GB Mac), or set `assumed_vram_gb` manually.

## MoE and reasoning models

| Tag pattern | Notes |
| --- | --- |
| `qwen3:30b-a3b` | ~20 GB hint in registry; acts like “big” below dense 30b VRAM |
| `deepseek-r1:*` | Bias toward **reasoning** tier in your agent; size varies by pull |
| `phi4-reasoning:14b` | Heuristic weight from `:14b`; good reasoning slot on 12–16 GB |

Routing uses **prompt keywords** for tier (`step by step`, `design`, …), not model family. A `deepseek-r1` tag does not auto-route to reasoning unless the prompt matches.

## Mixing families vs single vendor

| Approach | Pros | Cons |
| --- | --- | --- |
| **All Qwen** | Consistent style; easy weights | Less flexibility per tier |
| **All Gemma** | Great small models | Fewer native large locals |
| **Mixed** | Best model per tier | Slightly uneven “voice” across steps |

split-stack only requires **two or more models with different weights** for routing to spread.

## Adding your own tags

Minimal config snippet:

```json
{
  "deployment_profile": "workstation_12gb",
  "models": [
    { "match": "my-router", "weight": 2000, "vram_gb": 3, "family": "custom" },
    { "match": "my-workhorse", "weight": 14000, "vram_gb": 10, "family": "custom" }
  ]
}
```

`match` is substring. Longer/more specific patterns win over shorter ones in the registry.

Verify:

```bash
stack models --json
stack route --prompt "your prompt" --json --models my-router,my-workhorse
```

## What we deliberately do not built-in

- Cloud model IDs (`gpt-4o`, `claude-3-5-sonnet`) — use gateway + `datacenter` profile
- Every Ollama library tag — heuristics + your config scale better
- Auto VRAM detection from GPU — advisory preset only (honest scope)
- **Per-prompt quant routing** — use `quant=` session-wide; see README Quantization section

## Gemma 4 QAT (Apr 2026)

Quantization-aware training checkpoints for Gemma 4 (E2B, E4B, 12B, 26B-A4B, 31B). split-stack tracks **runtime GB** when you set `quant="qat"`:

| Tag | QAT runtime (GB) | Default registry (GB) |
| --- | --- | --- |
| `gemma4:e4b` | 5 | 4 |
| `gemma4:12b` | 7 | 10 |
| `gemma4:26b-a4b` | 15 | 20 |
| `gemma4:31b` | 18 | 28 |

Sources: [Google Q4_0 collection](https://huggingface.co/collections/google/gemma-4-qat-q4_0), [Unsloth QAT analysis](https://unsloth.ai/docs/models/gemma-4/qat#qat-analysis) (prefer **UD-Q4_K_XL** over naive Q4_0 for llama.cpp), [mobile mixture](https://huggingface.co/collections/google/gemma-4-qat-mobile) (`quant="qat_mobile"`).

**Wrong use:** lowering model weight because Q4 is smaller — that sends complex prompts to the lookup slot. **Right use:** `quant="qat"` so `stack doctor` and `configure()` know `26b-a4b` fits 16 GB.

## See also

- [`../config/models.example.json`](../config/models.example.json) — full template
- [`DATACENTER.md`](DATACENTER.md) — fleet / dual-GPU
- [`../examples/quickstart/README.md`](../examples/quickstart/README.md) — hands-on tour
