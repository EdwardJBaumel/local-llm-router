# Ollama benchmark evidence (16 GB workstation)

Measured on **NVIDIA RTX 5070 Ti (16 GB)** with Ollama. Four synthetic agent steps per model — structured JSON extract, reasoning JSON, short digest, cover-style prose.

Raw data: [`scripts/ollama_benchmark/benchmark_results.json`](../scripts/ollama_benchmark/benchmark_results.json).

Re-run:

```bash
python scripts/ollama_benchmark/benchmark_models.py
```

## Summary (sanitized latencies)

| Model | Parse JSON | Analyze JSON | Parse ms | Analyze ms | Router tier fit |
| --- | --- | --- | --- | --- | --- |
| `gemma4:e4b` | 100% | 100% | **~1.4s** | ~10s | **lookup / simple extract** |
| `qwen3:8b` | 100% | 100% | ~6.7s | ~6.6s | **medium / default spine** |
| `qwen3:14b` | 100% | 100% | ~9.7s | ~11s | **complex / reason JSON** |
| `deepseek-r1:8b` | 33% | 100% | ~8.6s | ~9.5s | **reason + prose only** (not structured extract) |
| `gemma4:12b` | 0% | 100% | ~13s | ~16s | Skip for JSON stages |

## Recommended stacks

### 16 GB — mixed specialist (default)

| Router hint | Model | Why |
| --- | --- | --- |
| `lookup`, simple `code` | `gemma4:e4b` or `qwen3:8b` | 100% JSON; Gemma fastest on extract |
| `reason`, complex JSON | `qwen3:14b` | 100% JSON; fewer tokens than 8B on hard steps |
| `explain`, prose | `qwen3:14b` or `gemma4:e4b` | Best digest structure in bench |
| `reason` prose | `deepseek-r1:8b` | Highest cover-letter quality score |

Matches `llm-router stacks --profile workstation_16gb`.

### One model (simplest)

`qwen3:8b` for every step — predictable, fits 16 GB with headroom.

### Do not use on 16 GB for agent loops

| Model | Why |
| --- | --- |
| `deepseek-r1:8b` on JSON extract | Thinking trace breaks JSON (~33% valid) |
| `gemma4:12b` on JSON extract | 0% valid JSON in bench (thinking overhead) |
| `gemma4:31b` | Loads ~15 GB VRAM; 3–4 min/call vs ~10s for `qwen3:14b` |
| Tesla P40 etc. | VRAM/$ win only; much slower than modern 16 GB cards for ≤14B |

## Model families (DeepSeek distilled)

`deepseek-r1:8b` on Ollama is **R1-0528 distilled onto Qwen3-8B**. Use it when you want reasoning-style steps, not when you need strict JSON without a `/no_think` or non-thinking mode.

Try `deepseek-r1:14b` as an alternative to `qwen3:14b` on the **reason** tier if analyse quality matters more than latency.

## How this feeds routing

local-llm-router does not run these benchmarks automatically. Use this doc to:

1. Pick models in `local-llm-router.models.json` or `configure(vram_gb=16)`.
2. Validate with `llm-router doctor --check-stack --vram-gb 16`.
3. Re-benchmark when you change GPU or pull new quants.

See also: [`local-models.md`](local-models.md).
