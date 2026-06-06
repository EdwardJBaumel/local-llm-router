# Integrating split-stack

split-stack is a **routing library**: it picks `(tier, model_tag)` before each LLM call. It does not run inference, tools, or memory.

## One engine, two entry points

Both paths call the same `explain_route()` core. Pick based on who owns the model list.

| Pattern | Who | Setup | Per step |
| --- | --- | --- | --- |
| **Session (embedded)** | App devs | `configure()` once | `route()` / `explain()` |
| **Explicit (power user)** | Gateways, tests | `assign_tiers(models)` | `route_prompt()` / `explain_route()` |

**Embedded apps:** import is silent by default. Use `stack tips` in dev, or `SPLIT_STACK_IMPORT_TIPS=on` for one-time stderr tips.

### Progressive disclosure (same session API)

You stay on `configure()` → `route()` until you need more control:

| Level | When | Example |
| --- | --- | --- |
| **0 — preset** | Trust the 16 GB ladder | `configure(vram_gb=16, quant="qat")` |
| **1 — explicit models** | You know your tags | `configure(vram_gb=16, models=[...])` |
| **2 — custom ladder** | Pin slots yourself | `configure(..., models=[...], tiers=TierMap(...))` |
| **3 — no session** | Full ownership, no globals | `route_prompt(text, assign_tiers([...]), hint=...)` |

Level 3 is for gateways and unit tests. Levels 0–2 share env vars, warnings, and `describe_session()` logging.

---

## Convenient: configure once

```python
import split_stack

split_stack.configure(
    vram_gb=16,
    quant="qat",
    models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"],  # explicit list recommended
)

for step in agent_steps:
    tier, model = split_stack.route(step.prompt, hint=step.kind)
    response = your_ollama_client.generate(model=model, prompt=step.prompt)
```

Environment (optional):

```bash
export SPLIT_STACK_VRAM_GB=16
export SPLIT_STACK_QUANT=qat
# export SPLIT_STACK_PROFILE=workstation_16gb
```

### Validate after configure

```python
session = split_stack.configure(vram_gb=16, models=[...])
for warning in session.warnings:
    logging.warning("split_stack: %s", warning)
```

### Custom tier ladder (level 2)

```python
from split_stack import TierMap, configure, route

configure(
    vram_gb=16,
    quant="qat",
    models=[
        "gemma4:e4b",
        "qwen3:8b",
        "qwen3:14b",
        "deepseek-coder:6.7b",
    ],
    tiers=TierMap(
        simple="gemma4:e4b",
        medium="qwen3:8b",
        complex="qwen3:14b",
        reasoning="qwen3:14b",
        code="deepseek-coder:6.7b",
    ),
)
tier, model = route(step.prompt, hint="code")
```

Or CLI:

```bash
stack explain --prompt "what is JWT?" --hint lookup --profile workstation_16gb --quant qat --json
```

---

## Power user: explicit tier map

```python
from split_stack import assign_tiers, explain_route, route_prompt

tiers = assign_tiers([
    "gemma4:e4b",
    "qwen3:8b",
    "qwen3:14b",
    "deepseek-coder-v2:16b",  # optional code slot
    "deepseek-r1:8b",         # optional reason slot
])

decision = explain_route(step.prompt, tiers, hint="code")
tier, model = decision.tier, decision.model
# or: tier, model = route_prompt(step.prompt, tiers, hint="code")
```

Custom registry: copy `config/models.example.json` → `split-stack.models.json` or set `SPLIT_STACK_MODELS_CONFIG`.

---

## Agent loop logging (recommended JSON shape)

Log once at startup:

```json
{
  "event": "split_stack.session",
  "profile": "workstation_16gb",
  "quant": "qat",
  "models": ["gemma4:e4b", "qwen3:8b", "qwen3:14b"],
  "tiers": {"simple": "gemma4:e4b", "medium": "qwen3:8b", "complex": "qwen3:14b", "reasoning": "qwen3:14b", "code": null},
  "warnings": ["No code specialist in models= — hint='code' uses the complex tier (qwen3:14b)."]
}
```

Log every step:

```python
decision = split_stack.explain(step.prompt, hint=step.kind)
log.info({"event": "split_stack.route", **decision.to_dict()})
tier, model = decision.tier, decision.model
```

Or minimal:

```python
tier, model = split_stack.route(step.prompt, hint=step.kind)
```

---

## Hints (required for efficiency)

| hint | tier | Typical model (3-model stack) |
| --- | --- | --- |
| `lookup` | simple | gemma4:e4b |
| `explain` | medium | qwen3:8b |
| `design` | complex | qwen3:14b |
| `code` | complex + code slot | coder if in `models=`, else qwen3:14b |
| `reason` | reasoning | R1/phi-reasoning if in `models=`, else qwen3:14b |

Your orchestrator should set `hint=` when it knows the step type. Without hints, keyword heuristics guess (fine for demos, bad for production).

---

## CLI checklist for new devs

```bash
pip install -e ".[ollama]"

stack stacks --profile workstation_16gb --quant qat
stack explain --prompt "what is JWT?" --hint lookup \
  --models gemma4:e4b,qwen3:8b,qwen3:14b --json

python examples/agent_runner/run.py --verbose --vram-gb 16 --quant qat \
  --models gemma4:e4b,qwen3:8b,qwen3:14b
```

---

## What split-stack does not do

- Pick quant per prompt (set `quant=` once)
- Detect GPU automatically (you pass `vram_gb`)
- Run chat/tools/history (your client)
- Guarantee benchmark optimality (presets are starting points)

See also: [`LOCAL_MODELS.md`](LOCAL_MODELS.md), [`examples/agent_runner/run.py`](../examples/agent_runner/run.py).
