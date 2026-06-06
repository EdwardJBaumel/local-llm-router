"""Session and tier-map validation — warnings, not hard failures."""

from __future__ import annotations

from split_stack.model_registry import load_registry, model_weight
from split_stack.models import TierMap
from split_stack.tiering import describe_tiers


def _is_reasoning_specialist(name: str) -> bool:
    lowered = name.lower()
    return "deepseek-r1" in lowered or "reasoning" in lowered or ":r1" in lowered


def _is_code_specialist(name: str) -> bool:
    lowered = name.lower()
    if "reasoning" in lowered:
        return False
    tokens = ("codellama", "deepseek-coder", "starcoder", "codegemma", "coder")
    return any(token in lowered for token in tokens)


def validate_tier_map(
    tiers: TierMap,
    models: list[str] | tuple[str, ...],
    *,
    profile: str | None = None,
) -> list[str]:
    """Return human-readable warnings about a tier ladder."""
    warnings: list[str] = []
    model_list = list(models)
    registry = load_registry(profile=profile)

    if len(model_list) < 2:
        warnings.append("Fewer than two models — routing cannot spread across tiers.")

    slot_models = {
        tiers.simple,
        tiers.medium,
        tiers.complex,
        tiers.reasoning,
    }
    if tiers.code:
        slot_models.add(tiers.code)
    unique_slots = len(slot_models)
    if unique_slots < min(3, len(model_list)):
        warnings.append(
            "Multiple tier slots map to the same model — spread is mostly cosmetic."
        )

    reasoning_specialists = [name for name in model_list if _is_reasoning_specialist(name)]
    if not reasoning_specialists and tiers.reasoning == tiers.complex:
        warnings.append(
            "No reasoning specialist in models= — hint='reason' uses the complex model "
            f"({tiers.complex}), not a dedicated reasoner."
        )

    code_specialists = [name for name in model_list if _is_code_specialist(name)]
    if not code_specialists:
        warnings.append(
            "No code specialist in models= — hint='code' uses the complex tier "
            f"({tiers.complex}) unless the prompt looks like code."
        )

    try:
        simple_w = model_weight(tiers.simple, registry)
        medium_w = model_weight(tiers.medium, registry)
        if simple_w > medium_w:
            warnings.append(
                f"Simple slot ({tiers.simple}, weight {simple_w}) is heavier than "
                f"medium ({tiers.medium}, weight {medium_w}) — check registry rows for "
                "unknown tags (heuristic weight 1000)."
            )
    except Exception:
        pass

    described = describe_tiers(tiers)
    if tiers.simple != model_list[0] and len(model_list) >= 2:
        ranked = sorted(model_list, key=lambda name: model_weight(name, registry))
        if tiers.simple != ranked[0]:
            warnings.append(
                f"Simple slot is {tiers.simple}; lightest installed tag is {ranked[0]}."
            )

    return warnings
