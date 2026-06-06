from __future__ import annotations

from split_stack.complexity import (
    looks_like_code,
    resolve_tier,
    score_prompt,
)
from split_stack.hints import normalize_step_kind, prefer_code_model
from split_stack.models import ComplexityTier, RouteDecision, StepKind, TierMap
from split_stack.tiering import describe_tiers


def route_prompt(
    prompt: str,
    tiers: TierMap,
    *,
    hint: str | StepKind | None = None,
) -> tuple[ComplexityTier, str]:
    """Return complexity tier and selected model for a prompt."""
    return explain_route(prompt, tiers, hint=hint).as_tuple()


def explain_route(
    prompt: str,
    tiers: TierMap,
    *,
    hint: str | StepKind | None = None,
) -> RouteDecision:
    """Return tier, model, and a trace of why routing chose them."""
    raw_hint = hint.value if isinstance(hint, StepKind) else hint
    step_kind: StepKind | None = None
    tier_source = "heuristic"
    reasons: list[str] = []

    if hint is not None:
        step_kind = normalize_step_kind(hint)
        tier = resolve_tier(prompt, hint=step_kind)
        tier_source = "hint"
        reasons.append(f"hint={step_kind.value} maps to tier {tier.value}")
    else:
        tier = score_prompt(prompt)
        reasons.append(f"no hint — keyword/heuristic scoring → tier {tier.value}")
        if len((prompt or "").split()) > 80:
            reasons.append("prompt length > 80 tokens influenced complex tier")

    use_code = _should_use_code_model(prompt, tier, hint, step_kind, tiers)
    if use_code and tiers.code:
        model = tiers.code
        model_source = "code_slot"
        if prefer_code_model(hint) or step_kind == StepKind.CODE:
            reasons.append(f"code specialist {model} (hint={step_kind.value if step_kind else hint})")
        else:
            reasons.append(f"code specialist {model} (prompt looks like code)")
    elif use_code and not tiers.code:
        model = tiers.for_tier(tier)
        model_source = "tier_slot"
        reasons.append(
            f"code-like prompt but no code slot — using {tier.value} model {model}"
        )
    else:
        model = tiers.for_tier(tier)
        model_source = "tier_slot"
        slot_name = tier.value
        if tier == ComplexityTier.REASONING and tiers.reasoning == tiers.complex:
            reasons.append(
                f"reasoning tier → {model} (no separate reasoning model; complex fallback)"
            )
        else:
            reasons.append(f"{slot_name} slot → {model}")

    return RouteDecision(
        tier=tier,
        model=model,
        hint=raw_hint,
        step_kind=step_kind.value if step_kind else None,
        tier_source=tier_source,
        model_source=model_source,
        reasons=tuple(reasons),
        tiers=describe_tiers(tiers),
    )


def _should_use_code_model(
    prompt: str,
    tier: ComplexityTier,
    hint: str | StepKind | None,
    step_kind: StepKind | None,
    tiers: TierMap,
) -> bool:
    if prefer_code_model(hint) or step_kind == StepKind.CODE:
        return True
    if tiers.code is None:
        return False
    if tier not in (ComplexityTier.COMPLEX, ComplexityTier.MEDIUM):
        return False
    return looks_like_code(prompt)
