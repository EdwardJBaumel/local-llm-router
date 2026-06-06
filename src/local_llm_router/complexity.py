from __future__ import annotations

from local_llm_router.hints import normalize_step_kind, prefer_code_model, tier_from_step_kind
from local_llm_router.models import ComplexityTier, StepKind

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
DEFAULT_SHELL_MARKERS = (
    "bash",
    "shell",
    "terminal",
    "command line",
    "run ",
    "execute ",
    "list files",
    "list the project root",
    "directory",
    "npm ",
    "pip ",
    "git ",
    "cargo ",
    "make ",
    "pytest",
)


def score_prompt(prompt: str, *, mode: str | None = None) -> ComplexityTier:
    return resolve_tier(prompt, mode=mode)


def resolve_tier(
    prompt: str,
    *,
    hint: StepKind | str | None = None,
    mode: str | None = None,
) -> ComplexityTier:
    step_kind = normalize_step_kind(hint) if hint is not None else None
    if step_kind is not None:
        return tier_from_step_kind(step_kind)

    text = (prompt or "").strip().lower()
    if not text:
        return ComplexityTier.SIMPLE

    if looks_like_shell_work(prompt):
        tier = ComplexityTier.COMPLEX
    elif any(marker in text for marker in DEFAULT_REASONING_MARKERS):
        tier = ComplexityTier.REASONING
    elif any(marker in text for marker in DEFAULT_COMPLEX_MARKERS) or len(text.split()) > 80:
        tier = ComplexityTier.COMPLEX
    elif any(marker in text for marker in DEFAULT_MEDIUM_MARKERS):
        tier = ComplexityTier.MEDIUM
    elif len(text.split()) <= 8 and text.endswith("?"):
        tier = ComplexityTier.SIMPLE
    elif len(text.split()) > 25:
        tier = ComplexityTier.MEDIUM
    else:
        tier = ComplexityTier.SIMPLE

    return _apply_mode_cap(tier, prompt, mode)


def _apply_mode_cap(
    tier: ComplexityTier,
    prompt: str,
    mode: str | None,
) -> ComplexityTier:
    """In chat mode, cap heuristic tiers at MEDIUM unless shell/code is explicit."""
    if mode != "chat":
        return tier
    if tier not in (ComplexityTier.COMPLEX, ComplexityTier.REASONING):
        return tier
    if looks_like_code(prompt) or looks_like_shell_work(prompt):
        return tier
    return ComplexityTier.MEDIUM


def looks_like_code(prompt: str) -> bool:
    text = (prompt or "").lower()
    return any(marker in text for marker in DEFAULT_CODE_MARKERS)


def looks_like_shell_work(prompt: str) -> bool:
    text = (prompt or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in DEFAULT_SHELL_MARKERS)
