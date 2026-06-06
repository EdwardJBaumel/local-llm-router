# For app authors

**split-stack is a model picker for local LLM apps.** It does not run inference, chat, or tools. Your app still calls Ollama (or LM Studio, llama.cpp, etc.). split-stack only answers:

> *Which model tag should this step use?*

Use it when your app runs **more than one local model** and step difficulty varies — or when you want a **default rule** instead of hardcoding `if easy: model_a else: model_b` everywhere.

---

## When to add it

| Good fit | Skip it |
| --- | --- |
| Chat / copilot — user asks anything | Single-button tool — same task every time |
| Multi-step agent — lookup, plan, design, code | One model already works fine |
| Mixed ops UI — quick check vs deep analysis | Cloud-only API with one model |
| You have 2–3 Ollama models and hate always using the biggest | You never change models |

**Shorthand use:** you are not sure how hard the next step will be, but you *do* know (or can guess) the **kind** of step — fact lookup, explain, design, code, reason. Pass that as `hint=` and split-stack maps it to a tier and model name.

---

## Install

```bash
pip install split-stack
```

Optional Ollama helpers (`stack ask`, disk discovery):

```bash
pip install "split-stack[ollama]"
```

From GitHub before PyPI:

```bash
pip install git+https://github.com/edwardjbaumel/split-stack.git
```

---

## Minimal integration (Python)

**Once** at app startup:

```python
import split_stack

split_stack.configure(vram_gb=16)  # your GPU budget in GB
```

**Before every LLM call:**

```python
tier, model = split_stack.route(prompt, hint="lookup")
response = your_client.generate(model=model, prompt=prompt)
```

`hint` is the shorthand. You choose it from what the step *is*, not from the model:

| `hint=` | Typical use |
| --- | --- |
| `lookup` | Facts, yes/no, one-liner |
| `explain` | Summarize, compare, plan |
| `design` | Architecture, strategy, drafts |
| `code` | Write or fix code |
| `reason` | Step-by-step proof, scoring |

Omit `hint` only for demos — split-stack guesses from keywords (less reliable in production).

---

## Not sure about the outcome?

Two patterns:

**1. You know the step type (most apps)**  
Your UI, queue, or pipeline already labels the job → map label to `hint` → `route()`.

```python
HINT_FOR_JOB = {
    "check_keyword": "lookup",
    "summarize": "explain",
    "draft_plan": "design",
}

hint = HINT_FOR_JOB[job_type]
tier, model = split_stack.route(prompt, hint=hint)
```

**2. You truly don't know**  
Use `hint=None` for a heuristic guess, or classify first (rules / small model / user pick), then call `route()` with the hint. split-stack is the **model** shorthand, not the **intent** classifier.

---

## Explicit model list (recommended)

Presets are a starting point. Production apps should pin tags:

```python
split_stack.configure(
    vram_gb=16,
    quant="qat",
    models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"],
)
```

---

## Not Python?

Shell out to the CLI and parse JSON:

```bash
stack route --prompt "what is JWT?" --hint lookup --json \
  --models gemma4:e4b,qwen3:8b,qwen3:14b
```

Same routing logic; your app reads `tier` and `model` from stdout.

---

## Logging (optional)

```python
decision = split_stack.explain(prompt, hint=hint)
log.info({"event": "split_stack.route", **decision.to_dict()})
tier, model = decision.tier, decision.model
```

---

## What split-stack is not

- Not an Ollama plugin — Ollama just receives the model name you pass
- Not an agent framework — no memory, tools, or orchestration
- Not cloud routing — built for local VRAM budgets
- Not per-prompt quantization — set `quant=` once at configure time

---

## Next steps

- Full integration patterns: [`INTEGRATION.md`](INTEGRATION.md)
- Copy-paste demo: [`examples/agent_runner/patterns.py`](../examples/agent_runner/patterns.py)
- Compare POC (why not always use the biggest model?): [`examples/poc_compare/`](../examples/poc_compare/)
- Publish / version: [`PUBLISHING.md`](PUBLISHING.md)
