# Embed split-stack in your script

Shows the smallest useful embed: import routing, call Ollama, print tier + model + answer.

Use this pattern in **your own project repo** (portfolio site, SaaS side project, etc.). split-stack stays a dependency; your product name and repo stay yours.

## Run

From the `split_stack` repo root:

```bash
python -m pip install -e ".[ollama]"
stack requirements local_assistant --check
python "examples/embed_script/copy_helper.py" "suggest 3 taglines for a developer portfolio"
```

## Copy into your project

1. `pip install split-stack[ollama]` (or editable install from this repo)
2. Copy `ask_local()` from `copy_helper.py` into `scripts/ask.py` in your repo
3. Keep Cursor on Auto for code; run your script for cheap local copy/planning prompts

## Other examples

- Interactive demo: [`examples/local_work_assistant/`](../local_work_assistant/)
- IDE panel: [`extension/vscode/`](../../extension/vscode/)
