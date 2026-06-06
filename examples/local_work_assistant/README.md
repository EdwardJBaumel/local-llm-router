# Local work assistant (perfect use case)

This example shows the most practical use case for `split-stack`:

- Keep Cursor native for agentic coding
- Use local routing for direct work questions and script tasks
- Automatically route simple prompts to smaller local models and complex prompts to larger ones

## Why this is the right use case

The app handles the exact prompts people ask all day:

- quick definitions and summaries
- implementation planning and architecture tradeoffs
- debugging and refactoring prompts

It gives the "auto model selection" feel without adding a paid proxy service.

## Run

From the `split_stack` directory:

```bash
python -m pip install -e ".[ollama]"
stack requirements local_assistant --check
python "examples/local_work_assistant/app.py"
```

Or run one prompt:

```bash
python "examples/local_work_assistant/app.py" --prompt "design a retry strategy for webhook processing"
```

## What you will see

1. Detected model tiers from Ollama tags
2. Prompt complexity tier selected by `split_stack.route_prompt()`
3. Final model chosen for that tier
4. Generated response from Ollama

Example output:

```text
Loaded model tiers
  SIMPLE:    gemma4:e4b
  MEDIUM:    qwen3:8b
  COMPLEX:   qwen3:30b-a3b
  REASONING: qwen3:30b-a3b

> what is eventual consistency?

Routed to gemma4:e4b (simple)
...
```
