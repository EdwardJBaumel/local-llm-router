# Agent runner POC

Shows how to wire split-stack into a **multi-step agent loop**: one routing call before each LLM step.

Full integration guide: [`docs/INTEGRATION.md`](../../docs/INTEGRATION.md)

## See all four API levels (dry run)

```bash
cd split-stack
python examples/agent_runner/patterns.py
```

## Dry run — default (session preset, 16 GB + QAT)

```bash
python examples/agent_runner/run.py
python examples/agent_runner/run.py --verbose
```

```text
[step 1/5] understand_goal: tier=medium model=qwen3:8b hint=explain
[step 2/5] quick_lookup: tier=simple model=gemma4:e4b hint=lookup
[step 3/5] compare_options: tier=medium model=qwen3:8b hint=explain
[step 4/5] design: tier=complex model=qwen3:14b hint=design
[step 5/5] reason: tier=reasoning model=qwen3:14b hint=reason
```

## CLI modes

| Flag | Level | What it does |
| --- | --- | --- |
| *(none)* | 0 | `configure(vram_gb=16, quant="qat")` |
| `--models a,b,c` | 1 | `configure(..., models=[...])` |
| `--custom-tiers` | 2 | `configure(..., tiers=TierMap(...))` with code slot |
| `--explicit --models a,b,c` | 3 | `assign_tiers` + `explain_route` (no session) |

```bash
python examples/agent_runner/run.py --models gemma4:e4b,qwen3:8b,qwen3:14b --verbose
python examples/agent_runner/run.py --custom-tiers --verbose
python examples/agent_runner/run.py --explicit --models gemma4:e4b,qwen3:8b,qwen3:14b
```

## Live run (Ollama)

```bash
pip install -e ".[ollama]"
python examples/agent_runner/run.py --live --models gemma4:e4b,qwen3:8b,qwen3:14b
```

## Compare POC (routing vs always-largest)

```bash
python examples/poc_compare/run.py
stack compare
```

Browser UI: `python examples/demo_ui/server.py`
