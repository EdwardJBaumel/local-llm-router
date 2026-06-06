# split-stack

**A Python routing library for local LLM agent loops.**

Give split-stack a prompt and your model list. It returns a complexity tier and which model to call. You keep your agent runner, gateway, or Ollama client — split-stack only decides *which* local model each step should use.

Zero runtime dependencies. Works offline. No inference, no agent framework, no chat UI.

```python
import split_stack

split_stack.configure(vram_gb=16, quant="qat")  # once — or export SPLIT_STACK_VRAM_GB=16

for step in agent_steps:
    tier, model = split_stack.route(step.prompt, hint=step.hint)
    response = your_llm.complete(model=model, prompt=step.prompt)
```

Or pass an explicit model list:

```python
from split_stack import assign_tiers, route_prompt

tiers = assign_tiers(["qwen3:4b", "qwen3:8b", "qwen3:14b"])

for step in agent_steps:
    tier, model = route_prompt(step.prompt, tiers, hint=step.hint)
    response = your_llm.complete(model=model, prompt=step.prompt)
```

## What it is

| Piece | Role |
| --- | --- |
| **`score_prompt(text)`** | Heuristic complexity tier (`simple` → `medium` → `complex` → `reasoning`) |
| **`assign_tiers(model_names)`** | Map your model names onto tier slots by size/name |
| **`route_prompt(text, tiers, hint=...)`** | Pick `(tier, model_name)` for one agent step |
| **`stack route` / `stack benchmark` / `stack compare`** | CLI for scripts, gateways, and CI evidence |

**Typical integration:** [`docs/FOR_APP_AUTHORS.md`](docs/FOR_APP_AUTHORS.md) (start here) · [`docs/INTEGRATION.md`](docs/INTEGRATION.md) (deeper patterns)

## Workstation size (VRAM)

split-stack maps **GPU VRAM (GB)** to a preset ladder. Devs are expected to know their budget; set it once:

```python
split_stack.configure(vram_gb=16)
```

Or:

```bash
export SPLIT_STACK_VRAM_GB=16   # Linux/macOS
$env:SPLIT_STACK_VRAM_GB=16    # PowerShell
```

| VRAM | Profile |
| --- | --- |
| ≤8 GB | `workstation_8gb` |
| ≤12 GB | `workstation_12gb` |
| ≤16 GB | `workstation_16gb` |
| ≤24 GB | `workstation_24gb` (3090 / 4090 class) |
| ≤32 GB | `workstation_32gb` |

**Apple Silicon:** there is no separate GPU VRAM — use **unified memory** as a conservative guide (e.g. 16 GB Mac → `vram_gb=12` or `16`, not 24). See [`docs/LOCAL_MODELS.md`](docs/LOCAL_MODELS.md) for preset details.

If you omit `models=`, split-stack picks a stack from the profile and what you have pulled in Ollama.

## Quantization (`quant=`)

**Critical:** split-stack does **not** pick Q4 vs Q8 per prompt. That would route hard steps to the wrong tier. Quant is a **pull-time** choice you declare once:

```python
split_stack.configure(vram_gb=16, quant="qat")
```

Or `$env:SPLIT_STACK_QUANT="qat"`.

| Mode | Meaning |
| --- | --- |
| `default` | Registry VRAM assumes typical Ollama Q4/Q5 pulls |
| `qat` | Gemma 4 QAT int4 runtime sizes (Unsloth [UD-Q4_K_XL](https://unsloth.ai/docs/models/gemma-4/qat#qat-analysis) table) |
| `qat_mobile` | Google mobile mixture QAT (E2B/E4B) |
| `bf16` | Full-precision Gemma 4 sizes for VRAM filter |

What `quant=` actually does:

1. **VRAM filter** — e.g. `gemma4:26b-a4b` fits 16 GB at QAT (~15 GB) but not at default (~20 GB).
2. **Stack suggestions** — `quant="qat"` adds `gemma4:26b-a4b` to the 16 GB preset ladder.
3. **Routing unchanged** — still `(tier, model_tag)`; your Ollama tag stays `gemma4:e4b`.

Ollama tags do not encode quant. If you pulled Unsloth QAT GGUFs into `gemma4:e4b`, set `quant="qat"` so feasibility math matches reality.

**Gemma 4 QAT pulls:** Google ships [Q4_0 GGUFs](https://huggingface.co/collections/google/gemma-4-qat-q4_0); Unsloth’s analysis shows naive Q4_0 conversion loses accuracy vs their [UD-Q4_K_XL](https://huggingface.co/collections/unsloth/gemma-4-qat) builds for llama.cpp/Ollama import. Mobile: [google/gemma-4-qat-mobile](https://huggingface.co/collections/google/gemma-4-qat-mobile).

```bash
stack models --profile workstation_16gb --quant qat --include-disk
stack stacks --profile workstation_16gb --quant qat
```

## What it is not

| This repo | Not this |
| --- | --- |
| Importable routing primitives | A consumer chat app |
| Owned heuristics you can test (`pytest`, no GPU) | Cursor chat interception or “save tokens on easy questions” |
| Optional Ollama helpers (`pip install -e ".[ollama]"`) | Another LiteLLM or multi-cloud proxy |
| Optional VS Code Quick Ask demo | An agent framework (no tools, memory, orchestration) |

**Primary user:** a developer building agent runners, gateways, or batch pipelines who already controls a local model list (usually Ollama).

## How routing works

```text
your prompt (+ optional step hint)
        ↓
score_prompt / resolve_tier     →  simple | medium | complex | reasoning
        ↓
assign_tiers(your model names)  →  tier → model map
        ↓
route_prompt(...)               →  (tier, model_name)
        ↓
your LLM client                 →  generate
```

Step hints (`lookup`, `explain`, `design`, `code`, `reason`) override keyword scoring when you know the agent phase. See [`docs/USER_STORIES.md`](docs/USER_STORIES.md).

## Proof (10-prompt benchmark)

Run locally — no inference, CI-safe:

```bash
pip install -e .
stack benchmark --markdown --models qwen3:4b,qwen3:8b,qwen3:14b
```

Example output on the fixed suite:

| id | tier | model | note |
| --- | --- | --- | --- |
| b01 | simple | qwen3:4b | definition |
| b02 | simple | qwen3:4b | definition |
| b03 | simple | qwen3:4b | short explain |
| b04 | medium | qwen3:8b | medium explain |
| b05 | medium | qwen3:8b | compare |
| b06 | medium | qwen3:8b | plan |
| b07 | complex | qwen3:14b | debug keyword |
| b08 | complex | qwen3:14b | architecture |
| b09 | complex | qwen3:14b | refactor keyword |
| b10 | reasoning | qwen3:14b | reasoning |

Naive “always use biggest model” sends **all 10** to `qwen3:14b`. split-stack spreads them across **3 models**.

## Compare POC (why not always 14b?)

Same 5-step agent loop, two strategies: **split-stack** (`route_prompt` per step) vs **baseline** (always the largest model). Dry by default — no Ollama:

```bash
stack compare
python examples/poc_compare/run.py
```

```text
Compare: split-stack vs always-largest (qwen3:14b)

 step              | routed tier | routed model | baseline model
 quick_lookup       | simple      | qwen3:4b     | qwen3:14b
 ...

Summary:
  split-stack:  3 models used, 3/5 steps avoided largest
  baseline:     1 model used, 5/5 on largest
```

Optional live latency on your hardware:

```bash
stack compare --live --models qwen3:4b,qwen3:8b,qwen3:14b
```

See [`examples/poc_compare/README.md`](examples/poc_compare/README.md).

## Visual demo (browser)

Interactive view of the same compare POC — tier badges, step cards, optional live latency bars. **Demo only**, not the product:

```bash
pip install -e ".[ollama]"
python examples/demo_ui/server.py
```

Open **http://127.0.0.1:8765**. Live mode needs models pulled (`ollama pull qwen3:4b` etc.); missing models show an actionable error, not a traceback.

See [`examples/demo_ui/README.md`](examples/demo_ui/README.md).

## Try it

**Agent runner (hero demo)** — five steps, different model per step:

```bash
pip install -e .
python examples/agent_runner/run.py
```

```text
[step 1/5] understand_goal: tier=medium model=qwen3:8b
[step 2/5] quick_lookup: tier=simple model=qwen3:4b
[step 3/5] compare_options: tier=medium model=qwen3:8b
[step 4/5] design: tier=complex model=qwen3:14b
[step 5/5] reason: tier=reasoning model=qwen3:14b
```

See [`examples/agent_runner/README.md`](examples/agent_runner/README.md).

**Quickstart tour** — config, dry routing, benchmark, optional live Ollama:

```powershell
.\examples\quickstart\try_it.ps1
.\examples\quickstart\try_it.ps1 --live
```

See [`examples/quickstart/README.md`](examples/quickstart/README.md).

## Install

**App authors (use in your project):**

```bash
pip install split-stack
pip install "split-stack[ollama]"   # optional: Ollama discovery, stack ask
```

**Contributors (this repo):**

```bash
pip install -e .
pip install -e ".[ollama]"
```

Before PyPI: `pip install git+https://github.com/edwardjbaumel/split-stack.git`

See [`docs/FOR_APP_AUTHORS.md`](docs/FOR_APP_AUTHORS.md) · [`docs/PUBLISHING.md`](docs/PUBLISHING.md)

First-time local setup (VRAM preset, Ollama pulls, `split-stack.models.json`):

```bash
stack setup --profile workstation_12gb
stack setup --profile 12gb --yes          # non-interactive
stack setup --profile 12gb --dry-run      # plan only
```

## Public API

**Session (embedded):**

- `configure(vram_gb=16, quant="qat", models=[...], tiers=...)` → set default profile + tier map (once per process)
- `route(prompt, hint="lookup")` → `(tier, model)` tuple
- `explain(prompt, hint="lookup")` → `RouteDecision` with reasons (logging / debug)
- `describe_session()` → active configure snapshot
- `session_warnings()` → warnings from last configure

**Explicit (power user):**

- `assign_tiers(model_names)` → tier map from model list
- `route_prompt(text, tiers, hint="lookup")` → `(tier, model)` with your tier map
- `explain_route(text, tiers, hint=...)` → full decision trace
- `validate_tier_map(tiers, models, profile=...)` → warning strings

**Shared:**

- `score_prompt(text)` → tier only, no network
- `assign_recommended_tiers("workstation_16gb")` → preset ladder
- `usage_requirements(profile, check=True)` → prerequisite catalog

CLI for gateways and polyglot glue:

```bash
stack route --prompt "design webhook retries" --json --models qwen3:4b,qwen3:8b,qwen3:14b
stack benchmark --json
stack compare
stack ask --prompt "what is caching?" --json    # optional: route + Ollama generate
```

## Local model table (optional)

For Ollama discovery and VRAM-aware filtering — not required for `route_prompt()` with your own model list.

```bash
stack models
stack doctor
copy config\models.example.json split-stack.models.json
```

Or `~/.config/split-stack/models.json` or `SPLIT_STACK_MODELS_CONFIG`. Presets: `stack profiles`. Guides: [`docs/LOCAL_MODELS.md`](docs/LOCAL_MODELS.md), [`docs/DATACENTER.md`](docs/DATACENTER.md).

## Integrations

- LiteLLM custom router: [`docs/integrations/litellm.md`](docs/integrations/litellm.md)
- VS Code / Cursor Quick Ask panel (optional demo, not the product): [`extension/vscode/README.md`](extension/vscode/README.md)

## Scope (v0.2)

**In scope:** tier heuristics, model mapping, agent-loop hook, benchmark evidence, pytest CI.

**Out of scope:** agent memory, tools, orchestration, Cursor proxy, cloud multi-provider policy.

## Docs and tests

- [`docs/PACKAGING_USER_GUIDE.md`](docs/PACKAGING_USER_GUIDE.md) — pip install for app devs
- [`docs/FOR_APP_AUTHORS.md`](docs/FOR_APP_AUTHORS.md) — one-page guide for other local LLM apps
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md) — session vs explicit API
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — PyPI checklist
- [`docs/SECURITY.md`](docs/SECURITY.md) — what not to commit
- [`docs/USER_STORIES.md`](docs/USER_STORIES.md)
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md)
- [`docs/NAMING_CONVENTIONS.md`](docs/NAMING_CONVENTIONS.md)
- [`docs/REPOSITORY.md`](docs/REPOSITORY.md) — how this repo relates to other projects on disk

```bash
pip install -e ".[dev]"
pytest
```

94 tests, no GPU required.

## Resume line

Built **split-stack**, a zero-dep Python routing library for agent loops; shipped a 10-prompt benchmark, compare POC (`stack compare`), and agent-runner demo showing per-step local model tiering (4B/8B/14B) instead of always using the largest model.

## Related projects

Same author, separate product: [Local Recruiting Ops](https://github.com/edwardjbaumel/local-recruiting-ops) (local job pipeline and dashboard). split-stack does not depend on it.

## Adoption

- **PyPI:** follow [`docs/PUBLISHING.md`](docs/PUBLISHING.md) → `pip install split-stack`
- **Other apps:** embed `configure()` + `route()` or call `stack route --json` — see [`docs/FOR_APP_AUTHORS.md`](docs/FOR_APP_AUTHORS.md)
- **Evidence:** compare POC + live agent runner on your hardware
