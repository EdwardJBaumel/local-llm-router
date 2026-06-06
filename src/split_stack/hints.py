"""Agent step hints for agent-loop routing."""

from __future__ import annotations

from split_stack.models import ComplexityTier, StepKind

# Five step types used in compare POC and agent-runner demos.
HINT_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "lookup",
        "tier": ComplexityTier.SIMPLE.value,
        "label": "Lookup",
        "summary": "Facts, definitions, one-liners",
    },
    {
        "id": "explain",
        "tier": ComplexityTier.MEDIUM.value,
        "label": "Explain",
        "summary": "Summarise, compare, outline, plan",
    },
    {
        "id": "design",
        "tier": ComplexityTier.COMPLEX.value,
        "label": "Design",
        "summary": "Architecture, strategy, tradeoffs",
    },
    {
        "id": "code",
        "tier": ComplexityTier.COMPLEX.value,
        "label": "Code",
        "summary": "Implement, refactor, debug (uses code slot when set)",
    },
    {
        "id": "reason",
        "tier": ComplexityTier.REASONING.value,
        "label": "Reason",
        "summary": "Proofs, step-by-step, formal logic",
    },
)

# Short-lived aliases from an earlier 4-hint experiment.
LEGACY_HINT_ALIASES: dict[str, str] = {
    "work": "explain",
    "build": "design",
}

_CANONICAL_IDS = frozenset(item["id"] for item in HINT_CATALOG)


def canonical_hint_id(hint: str | StepKind | None) -> str | None:
    if hint is None:
        return None
    if isinstance(hint, StepKind):
        raw = hint.value
    else:
        raw = hint.strip().lower()
    if raw in _CANONICAL_IDS:
        return raw
    if raw in LEGACY_HINT_ALIASES:
        return LEGACY_HINT_ALIASES[raw]
    return raw


def normalize_step_kind(hint: str | StepKind | None) -> StepKind | None:
    if hint is None:
        return None
    if isinstance(hint, StepKind):
        return hint
    lowered = hint.strip().lower()
    canonical = canonical_hint_id(lowered)
    if canonical is None:
        valid = ", ".join(item["id"] for item in HINT_CATALOG)
        raise ValueError(f"Unknown step hint '{hint}'. Valid hints: {valid}")
    try:
        return StepKind(canonical)
    except ValueError as exc:
        valid = ", ".join(item["id"] for item in HINT_CATALOG)
        raise ValueError(f"Unknown step hint '{hint}'. Valid hints: {valid}") from exc


def prefer_code_model(hint: str | StepKind | None) -> bool:
    if hint is None:
        return False
    raw = hint.value if isinstance(hint, StepKind) else hint.strip().lower()
    return raw == "code"


def tier_from_step_kind(kind: StepKind) -> ComplexityTier:
    lookup = {
        StepKind.LOOKUP: ComplexityTier.SIMPLE,
        StepKind.EXPLAIN: ComplexityTier.MEDIUM,
        StepKind.WORK: ComplexityTier.MEDIUM,
        StepKind.DESIGN: ComplexityTier.COMPLEX,
        StepKind.BUILD: ComplexityTier.COMPLEX,
        StepKind.CODE: ComplexityTier.COMPLEX,
        StepKind.REASON: ComplexityTier.REASONING,
    }
    return lookup[kind]


def list_hints() -> tuple[dict[str, str], ...]:
    return HINT_CATALOG
