from __future__ import annotations

from local_llm_router.model_registry import ModelRegistry, load_registry, model_weight
from local_llm_router.models import TierMap


def _is_code_specialist(name: str) -> bool:
    lowered = name.lower()
    if "reasoning" in lowered:
        return False
    tokens = ("codellama", "deepseek-coder", "starcoder", "codegemma", "coder")
    return any(token in lowered for token in tokens)


def _is_reasoning_specialist(name: str) -> bool:
    lowered = name.lower()
    return "deepseek-r1" in lowered or "reasoning" in lowered or ":r1" in lowered


def assign_tiers(model_names: list[str], registry: ModelRegistry | None = None) -> TierMap:
    if not model_names:
        raise ValueError("model_names must contain at least one model")

    reg = registry or load_registry()
    code_models = [name for name in model_names if _is_code_specialist(name)]
    general_models = [name for name in model_names if name not in code_models]
    if not general_models:
        general_models = list(model_names)
        code_models = []

    reasoning_models = [name for name in general_models if _is_reasoning_specialist(name)]
    core_models = [name for name in general_models if name not in reasoning_models]
    if not core_models:
        core_models = list(general_models)

    ranked = sorted(core_models, key=lambda name: model_weight(name, reg))
    simple = ranked[0]
    complex_model = ranked[-1]
    medium = ranked[1] if len(ranked) > 1 else ranked[0]

    if reasoning_models:
        reasoning = sorted(reasoning_models, key=lambda name: model_weight(name, reg))[-1]
    else:
        reasoning = complex_model

    code = None
    if code_models:
        code = sorted(code_models, key=lambda name: model_weight(name, reg))[-1]

    return TierMap(
        simple=simple,
        medium=medium,
        complex=complex_model,
        reasoning=reasoning,
        code=code,
    )


def describe_tiers(tiers: TierMap) -> dict[str, str | None]:
    return {
        "simple": tiers.simple,
        "medium": tiers.medium,
        "complex": tiers.complex,
        "complex_alt": tiers.complex_alt,
        "reasoning": tiers.reasoning,
        "code": tiers.code,
    }
