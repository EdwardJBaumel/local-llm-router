# Repository layout

**This repo is the public home for local-llm-router** — a Python library that routes agent-loop steps to the right local Ollama model.

```text
local-llm-router/
├── src/local_llm_router/     # library
├── scripts/ollama_benchmark/ # optional Ollama evidence scripts
├── examples/                 # demos (agent runner, compare UI, …)
├── docs/                     # integration + model guidance
└── config/                   # models.example.json
```

## Clone and verify

```bash
git clone https://github.com/edwardjbaumel/local-llm-router.git
cd local-llm-router
pip install -e ".[dev,ollama]"
pytest
```

```bash
git rev-parse --show-toplevel   # should end in local-llm-router
git remote -v                   # origin → local-llm-router.git only
```

## What this repo is not

- Not a chat app, job board, or Cursor plugin
- Not a monorepo of unrelated apps — one product, one GitHub repo

Historical note: an earlier job-pipeline app (`local-recruiting-ops`) was retired; routing evidence from that work lives in [`benchmark-evidence.md`](benchmark-evidence.md).

See also: [`security.md`](security.md) — what must not be committed.
