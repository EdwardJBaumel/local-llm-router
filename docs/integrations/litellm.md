# LiteLLM integration recipe

local-llm-router does not ship a LiteLLM plugin. Add a **custom router** in your gateway in ~15 lines.

## When to use

- You already proxy `/v1/chat/completions` through LiteLLM
- You want per-request local model tiering without a paid router SaaS
- You accept maintaining a small Python hook in your gateway repo

## Install

```bash
pip install local-llm-router litellm
```

## Custom router sketch

```python
from local_llm_router import assign_tiers, route_prompt

_tiers = assign_tiers(["qwen3:4b", "qwen3:8b", "qwen3:14b"])


def pick_model_for_messages(messages: list[dict]) -> str:
    last_user = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            last_user = message.get("content", "")
            break
    _, model = route_prompt(last_user, _tiers)
    return model


# Before litellm.completion(...):
# model = pick_model_for_messages(messages)
# litellm.completion(model=model, messages=messages, ...)
```

## What this gives you

- Transparent tier routing owned in your codebase
- Same heuristics as `llm-router route --json`
- No Cursor chat interception (keep IDE agents native)

## What this does not give you

- Agent memory, tools, or orchestration (your framework owns that)
- Cloud multi-provider policy (v0.2 scope is tier heuristics only)

## Verify routing without LiteLLM

```bash
llm-router route --prompt "design webhook retries" --json --models qwen3:4b,qwen3:8b,qwen3:14b
```

See also: [`examples/agent_runner/run.py`](../examples/agent_runner/run.py)
