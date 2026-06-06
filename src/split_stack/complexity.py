from __future__ import annotations

from split_stack.hints import normalize_step_kind, prefer_code_model, tier_from_step_kind
from split_stack.models import ComplexityTier, StepKind

DEFAULT_REASONING_MARKERS = (
    "step by step",
    "reason carefully",
    "prove",
    "formalize",
    "rigorous",
)
DEFAULT_COMPLEX_MARKERS = (
    "architecture",
    "distributed",
    "tradeoff",
    "debug",
    "refactor",
    "design",
)
DEFAULT_MEDIUM_MARKERS = (
    "explain",
    "summarise",
    "summarize",
    "compare",
    "outline",
    "plan",
)
DEFAULT_CODE_MARKERS = (
    "refactor",
    "debug",
    "implement",
    "function",
    "class ",
    "traceback",
    "syntax error",
    "unit test",
    "pytest",
    "```",
)


def score_prompt(prompt: str) -> ComplexityTier:
    return resolve_tier(prompt)


def resolve_tier(
    prompt: str,
    *,
    hint: StepKind | str | None = None,
) -> ComplexityTier:
    step_kind = normalize_step_kind(hint) if hint is not None else None
    if step_kind is not None:
        return tier_from_step_kind(step_kind)

    text = (prompt or "").strip().lower()
    if not text:
        return ComplexityTier.SIMPLE

    if any(marker in text for marker in DEFAULT_REASONING_MARKERS):
        return ComplexityTier.REASONING

    token_like_count = len(text.split())
    if token_like_count <= 8 and text.endswith("?"):
        return ComplexityTier.SIMPLE
    if any(marker in text for marker in DEFAULT_COMPLEX_MARKERS) or token_like_count > 80:
        return ComplexityTier.COMPLEX
    if any(marker in text for marker in DEFAULT_MEDIUM_MARKERS):
        return ComplexityTier.MEDIUM
    if token_like_count > 25:
        return ComplexityTier.MEDIUM
    return ComplexityTier.SIMPLE


def looks_like_code(prompt: str) -> bool:
    text = (prompt or "").lower()
    return any(marker in text for marker in DEFAULT_CODE_MARKERS)
