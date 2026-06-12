# Ollama stack benchmark

Reproducible evidence for per-task model picks on a **16 GB workstation** (RTX 5070 Ti).

Simulates four agent-loop step types that map to local-llm-router hints:

| Stage | Router hint | What it tests |
| --- | --- | --- |
| `parse` | `code` / structured extract | Strict JSON from messy text |
| `analyze` | `reason` | Structured reasoning JSON |
| `digest` | `explain` | Short analytical prose |
| `cover` | `explain` / `design` | Long-form grounded prose |

## Run

Requires a running Ollama on `http://127.0.0.1:11434`.

```bash
python scripts/ollama_benchmark/benchmark_models.py
python scripts/ollama_benchmark/benchmark_models.py --models qwen3:8b qwen3:14b gemma4:e4b
```

Outputs:

- `benchmark_results.json` — raw metrics
- `benchmark_meta.json` — GPU snapshot and run metadata

Human-readable summary: [`docs/benchmark-evidence.md`](../../docs/benchmark-evidence.md).
