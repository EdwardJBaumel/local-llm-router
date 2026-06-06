from __future__ import annotations

from local_llm_router.models import StackAdvice


def stack_recommendation(cursor_override_enabled: bool = False) -> StackAdvice:
    return StackAdvice(
        cursor_model="Auto",
        prose_path="Use Claude/ChatGPT native apps for prose-heavy work",
        local_path="Use local Ollama for private quick questions and scripts",
        warn_cursor_override=cursor_override_enabled,
    )
