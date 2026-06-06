# Using local-llm-router (pip install guide)

For **app developers** who want `pip install local-llm-router` — not for publishing to PyPI.

## Install

```bash
pip install local-llm-router
```

With Ollama helpers (`llm-router ask`, model discovery):

```bash
pip install "local-llm-router[ollama]"
```

Before PyPI (from GitHub):

```bash
pip install git+https://github.com/edwardjbaumel/local-llm-router.git
```

Requires **Python 3.10+**. No GPU required for routing (dry picks only).

## Verify

```bash
python -c "import local_llm_router; print(local_llm_router.__version__)"
llm-router route --prompt "what is JWT?" --hint lookup --json \
  --models gemma4:e4b,qwen3:8b,qwen3:14b
```

## Use in your app (minimum)

```python
import local_llm_router

local_llm_router.configure(vram_gb=16)

tier, model = local_llm_router.route("what is JWT?", hint="lookup")
# → then call your Ollama client with model=
```

## Environment variables (optional)

```bash
export local_llm_router_VRAM_GB=16
export local_llm_router_QUANT=qat
```

Then `local_llm_router.configure()` with no args picks them up.

## Where to go next

| Doc | For |
| --- | --- |
| [`for-app-authors.md`](for-app-authors.md) | When to use it, hints, examples |
| [`integration.md`](integration.md) | Session vs explicit API |
| [`local-models.md`](local-models.md) | VRAM presets and model tables |

## Publishing your own package (different topic)

If **you** are building a Python package to ship on PyPI, that is your project's packaging — local-llm-router is just a dependency:

```toml
# pyproject.toml in YOUR project
dependencies = ["local-llm-router>=0.2.0"]
```

Maintainers publishing **local-llm-router itself**: see [`publishing.md`](publishing.md).
