from __future__ import annotations

from local_llm_router.complexity import (
    looks_like_code,
    looks_like_shell_work,
    resolve_tier,
    score_prompt,
)
from local_llm_router.hints import normalize_step_kind, prefer_code_model
from local_llm_router.models import ComplexityTier, RouteDecision, StepKind, TierMap
from local_llm_router.tiering import describe_tiers


def _use_complex_primary(
    *,
    mode: str | None,
    hint: str | None,
    step_kind: StepKind | None,
) -> bool:
    """Agent-style work uses ``complex``; chat-style uses ``complex_alt`` when set."""
    if mode == "chat":
        return False
    if mode == "agent":
        return True
    if step_kind in (StepKind.DESIGN, StepKind.CODE, StepKind.BUILD):
        return True
    if hint in ("design", "code", "build"):
        return True
    return True


def _pick_tier_model(
    tier: ComplexityTier,
    tiers: TierMap,
    *,
    mode: str | None,
    hint: str | None,
    step_kind: StepKind | None,
) -> tuple[str, str]:
    if tier == ComplexityTier.COMPLEX and tiers.complex_alt:
        if _use_complex_primary(mode=mode, hint=hint, step_kind=step_kind):
            return tiers.complex, "complex_primary"
        return tiers.complex_alt, "complex_alt"
    return tiers.for_tier(tier), "tier_slot"


def route_prompt(
    prompt: str,
    tiers: TierMap,
    *,
    hint: str | StepKind | None = None,
    mode: str | None = None,
) -> tuple[ComplexityTier, str]:
    """Return complexity tier and selected model for a prompt."""
    return explain_route(prompt, tiers, hint=hint, mode=mode).as_tuple()


def explain_route(
    prompt: str,
    tiers: TierMap,
    *,
    hint: str | StepKind | None = None,
    mode: str | None = None,
) -> RouteDecision:
    """Return tier, model, and a trace of why routing chose them."""
    raw_hint = hint.value if isinstance(hint, StepKind) else hint
    step_kind: StepKind | None = None
    tier_source = "heuristic"
    reasons: list[str] = []

    if mode:
        reasons.append(f"mode={mode}")

    if hint is not None:
        step_kind = normalize_step_kind(hint)
        tier = resolve_tier(prompt, hint=step_kind, mode=mode)
        tier_source = "hint"
        reasons.append(f"hint={step_kind.value} maps to tier {tier.value}")
    else:
        tier = score_prompt(prompt, mode=mode)
        if looks_like_shell_work(prompt):
            reasons.append("shell/bash marker → complex tier")
        else:
            reasons.append(f"keyword/heuristic scoring → tier {tier.value}")
        if mode == "chat" and tier == ComplexityTier.MEDIUM:
            if resolve_tier(prompt, mode="agent") in (
                ComplexityTier.COMPLEX,
                ComplexityTier.REASONING,
            ) and not (looks_like_code(prompt) or looks_like_shell_work(prompt)):
                reasons.append("mode=chat — capped complex/reasoning tier to medium")
        if len((prompt or "").split()) > 80:
            reasons.append("prompt length > 80 tokens influenced complex tier")

    use_code = _should_use_code_model(prompt, tier, hint, step_kind, tiers)
    if use_code and tiers.code:
        model = tiers.code
        model_source = "code_slot"
        if prefer_code_model(hint) or step_kind == StepKind.CODE:
            reasons.append(f"code specialist {model} (hint={step_kind.value if step_kind else hint})")
        elif looks_like_shell_work(prompt):
            reasons.append(f"code specialist {model} (prompt looks like shell work)")
        else:
            reasons.append(f"code specialist {model} (prompt looks like code)")
    elif use_code and not tiers.code:
        model, model_source = _pick_tier_model(
            tier, tiers, mode=mode, hint=raw_hint, step_kind=step_kind
        )
        reasons.append(
            f"code-like prompt but no code slot — using {tier.value} model {model}"
        )
    else:
        model, model_source = _pick_tier_model(
            tier, tiers, mode=mode, hint=raw_hint, step_kind=step_kind
        )
        slot_name = tier.value
        if model_source == "complex_primary":
            reasons.append(
                f"complex slot → {model} (mode=agent or design/code hint)"
            )
        elif model_source == "complex_alt":
            reasons.append(f"complex_alt slot → {model} (mode=chat)")
        elif tier == ComplexityTier.REASONING and tiers.reasoning == tiers.complex:
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
        mode=mode,
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
    return looks_like_code(prompt) or looks_like_shell_work(prompt)
