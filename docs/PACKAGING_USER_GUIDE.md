# Using split-stack (pip install guide)

For **app developers** who want `pip install split-stack` — not for publishing to PyPI.

## Install

```bash
pip install split-stack
```

With Ollama helpers (`stack ask`, model discovery):

```bash
pip install "split-stack[ollama]"
```

Before PyPI (from GitHub):

```bash
pip install git+https://github.com/edwardjbaumel/split-stack.git
```

Requires **Python 3.10+**. No GPU required for routing (dry picks only).

## Verify

```bash
python -c "import split_stack; print(split_stack.__version__)"
stack route --prompt "what is JWT?" --hint lookup --json \
  --models gemma4:e4b,qwen3:8b,qwen3:14b
```

## Use in your app (minimum)

```python
import split_stack

split_stack.configure(vram_gb=16)

tier, model = split_stack.route("what is JWT?", hint="lookup")
# → then call your Ollama client with model=
```

## Environment variables (optional)

```bash
export SPLIT_STACK_VRAM_GB=16
export SPLIT_STACK_QUANT=qat
```

Then `split_stack.configure()` with no args picks them up.

## Where to go next

| Doc | For |
| --- | --- |
| [`FOR_APP_AUTHORS.md`](FOR_APP_AUTHORS.md) | When to use it, hints, examples |
| [`INTEGRATION.md`](INTEGRATION.md) | Session vs explicit API |
| [`LOCAL_MODELS.md`](LOCAL_MODELS.md) | VRAM presets and model tables |

## Publishing your own package (different topic)

If **you** are building a Python package to ship on PyPI, that is your project's packaging — split-stack is just a dependency:

```toml
# pyproject.toml in YOUR project
dependencies = ["split-stack>=0.2.0"]
```

Maintainers publishing **split-stack itself**: see [`PUBLISHING.md`](PUBLISHING.md).
