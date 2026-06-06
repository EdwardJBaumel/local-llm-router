from __future__ import annotations

from dataclasses import dataclass

from local_llm_router.model_registry import normalize_deployment_profile
from local_llm_router.models import TierMap
from local_llm_router.tiering import assign_tiers


@dataclass(frozen=True)
class RecommendedStack:
    profile: str
    models: tuple[str, ...]
    description: str
    tier_slots: dict[str, str] | None = None


RECOMMENDED_STACKS: dict[str, RecommendedStack] = {
    "workstation_8gb": RecommendedStack(
        profile="workstation_8gb",
        models=("gemma4:e4b", "qwen3.5:9b", "qwen2.5-coder:7b"),
        description="Gemma lookup + Qwen3.5 9B spine + coder on 8 GB",
    ),
    "workstation_12gb": RecommendedStack(
        profile="workstation_12gb",
        models=(
            "gemma4:e4b",
            "qwen3.5:9b",
            "qwen3:14b",
            "qwen2.5-coder:7b",
            "deepseek-r1:8b",
        ),
        description="Gemma lookup, Qwen3.5 mid, Qwen3 14B complex, coder + R1 reason",
    ),
    "workstation_16gb": RecommendedStack(
        profile="workstation_16gb",
        models=(
            "gemma4:e4b",
            "qwen3.5:9b",
            "qwen3.6:35b-a3b",
            "qwen3:14b",
            "qwen2.5-coder:14b",
            "deepseek-r1:8b",
        ),
        description="MoE complex for agent mode, dense 14B for chat (complex_alt)",
        tier_slots={
            "simple": "gemma4:e4b",
            "medium": "qwen3.5:9b",
            "complex": "qwen3.6:35b-a3b",
            "complex_alt": "qwen3:14b",
            "reasoning": "deepseek-r1:8b",
            "code": "qwen2.5-coder:14b",
        },
    ),
    "workstation_24gb": RecommendedStack(
        profile="workstation_24gb",
        models=(
            "gemma4:e4b",
            "qwen3.5:9b",
            "qwen3.6:27b",
            "qwen3:14b",
            "devstral-small:24b",
            "deepseek-r1:8b",
        ),
        description="Qwen3.6 27B agent complex + Devstral code + 14B chat alt",
        tier_slots={
            "simple": "gemma4:e4b",
            "medium": "qwen3.5:9b",
            "complex": "qwen3.6:27b",
            "complex_alt": "qwen3:14b",
            "reasoning": "deepseek-r1:8b",
            "code": "devstral-small:24b",
        },
    ),
    "workstation_32gb": RecommendedStack(
        profile="workstation_32gb",
        models=(
            "gemma4:e4b",
            "qwen3.5:9b",
            "qwen3.6:27b",
            "qwen3:14b",
            "devstral-small:24b",
            "deepseek-r1:8b",
            "gemma4:31b",
        ),
        description="5090 class: 27B agent + Devstral + optional Gemma 31B pull",
        tier_slots={
            "simple": "gemma4:e4b",
            "medium": "qwen3.5:9b",
            "complex": "qwen3.6:27b",
            "complex_alt": "qwen3:14b",
            "reasoning": "deepseek-r1:8b",
            "code": "devstral-small:24b",
        },
    ),
}


def list_recommended_stacks() -> tuple[RecommendedStack, ...]:
    return tuple(RECOMMENDED_STACKS[name] for name in sorted(RECOMMENDED_STACKS))


def recommended_models(profile: str, *, quant: str | None = None) -> list[str]:
    profile_name = normalize_deployment_profile(profile)
    stack = RECOMMENDED_STACKS.get(profile_name)
    if stack is None:
        valid = ", ".join(sorted(RECOMMENDED_STACKS))
        raise ValueError(f"Unknown profile '{profile}'. Valid workstation stacks: {valid}")
    from local_llm_router.quantization import expand_models_for_quant

    return expand_models_for_quant(list(stack.models), profile_name, quant)


def tier_map_from_slots(slots: dict[str, str]) -> TierMap:
    return TierMap(
        simple=slots["simple"],
        medium=slots["medium"],
        complex=slots["complex"],
        reasoning=slots["reasoning"],
        code=slots.get("code"),
        complex_alt=slots.get("complex_alt"),
    )


def assign_recommended_tiers(profile: str, *, quant: str | None = None) -> TierMap:
    profile_name = normalize_deployment_profile(profile)
    stack = RECOMMENDED_STACKS[profile_name]
    if stack.tier_slots:
        return tier_map_from_slots(stack.tier_slots)
    return assign_tiers(recommended_models(profile_name, quant=quant))
