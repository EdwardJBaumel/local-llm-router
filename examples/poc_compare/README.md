# Compare POC

Side-by-side proof: **split-stack routing** vs **always use the largest model** on the same 5-step agent loop.

Answers the main objection: *why not just run qwen3:14b on every step?*

## Dry run (default, no Ollama)

```bash
cd split-stack
python examples/poc_compare/run.py
```

Or via CLI:

```bash
stack compare
```

| Hint | Tier | Use for |
| --- | --- | --- |
| `lookup` | simple | Facts, one-liners (Gemma in mixed stack) |
| `explain` | medium | Summarise, compare, plan |
| `design` | complex | Architecture, strategy |
| `code` | complex | Refactor, debug (code slot when configured) |
| `reason` | reasoning | Proofs, step-by-step |

Default stack: **`gemma4:e4b,qwen3:8b,qwen3:14b`**

```text
Compare: split-stack vs always-largest (qwen3:14b)

 step              | routed tier | routed model | baseline model
 understand_goal    | medium      | qwen3:8b     | qwen3:14b
 quick_lookup       | simple      | gemma4:e4b   | qwen3:14b
 compare_options    | medium      | qwen3:8b     | qwen3:14b
 design             | complex     | qwen3:14b    | qwen3:14b
 reason             | reasoning   | qwen3:14b    | qwen3:14b

Summary:
  split-stack:  3 models used, 3/5 steps avoided largest
  baseline:     1 model used, 5/5 on largest
```

## Live run (Ollama latency, slow)

```bash
pip install -e ".[ollama]"
python examples/poc_compare/run.py --live --models qwen3:4b,qwen3:8b,qwen3:14b
stack compare --live
```

Runs each step twice (routed model, then baseline) and prints per-step and total latency. If a model is missing, you get a fix hint (`ollama pull …`) instead of a raw HTTP traceback.

## Visual browser demo

Same compare data in a local UI with tier colour badges and latency bars:

```bash
python examples/demo_ui/server.py
```

See [`../demo_ui/README.md`](../demo_ui/README.md).

## JSON

```bash
python examples/poc_compare/run.py --json
stack compare --json
```
