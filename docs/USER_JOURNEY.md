# User journey: side-project builder

You are building a passion-project site or app. You want cheap, private LLM help without burning Cursor quota on every small question.

split-stack does not replace Cursor. It routes the *other* prompts to the smallest local model that fits.

## The split stack for this workflow

| Task | Tool | Why |
| --- | --- | --- |
| Scaffold pages, fix bugs, run agents | Cursor on **Auto** | Agent + terminal + repo context |
| Tagline ideas, copy tweaks, "explain CSS grid" | **split-stack + Ollama** | Free, local, auto-picks small vs large model |
| Long prose drafts | Claude/ChatGPT app | Better writing UX than IDE chat |

## Day 0: one-time setup (~15 minutes)

```text
your-site/                   ← your repo (separate from split-stack)
split-stack/                 ← clone or pip install this library
Ollama                       ← local inference runtime
```

### 1. Install Ollama and pull two models

```bash
ollama pull qwen3:4b
ollama pull qwen3:8b
ollama serve
```

### 2. Install split-stack

```bash
cd split-stack
python -m pip install -e ".[ollama]"
stack requirements local_assistant --check
```

### 3. Smoke test

```bash
python "examples/embed_script/copy_helper.py" "suggest 5 taglines for a personal brand site"
```

Or use the VS Code / Cursor extension: **Split Stack: Quick Ask**.

## Day 1: wire it into your repo

```bash
cd ../your-site
pip install -e "../split-stack[ollama]"
```

Copy the `ask_local()` pattern from [`examples/embed_script/copy_helper.py`](../examples/embed_script/copy_helper.py) into `scripts/ask.py`.

## A normal afternoon

```text
09:00  Cursor Agent     "Create landing page with hero + projects grid"
10:00  python scripts/ask.py "three subtitle options under 12 words"
14:00  Cursor             "Wire newsletter form"
15:00  Quick Ask panel    "outline blog vs projects IA"
```

## Success criteria

1. Simple copy questions hit your smallest local model automatically
2. Planning prompts upgrade to a larger local model
3. Cursor Agent stays for repo edits only
4. `stack requirements local_assistant --check` stays green
