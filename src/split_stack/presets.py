from __future__ import annotations

from dataclasses import dataclass

from split_stack.model_registry import normalize_deployment_profile
from split_stack.models import TierMap
from split_stack.tiering import assign_tiers


@dataclass(frozen=True)
class RecommendedStack:
    profile: str
    models: tuple[str, ...]
    description: str


RECOMMENDED_STACKS: dict[str, RecommendedStack] = {
    "workstation_8gb": RecommendedStack(
        profile="workstation_8gb",
        models=("gemma4:e4b", "qwen3:8b"),
        description="Gemma min + Qwen 8b max (flat but honest on 8 GB)",
    ),
    "workstation_12gb": RecommendedStack(
        profile="workstation_12gb",
        models=("gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b"),
        description="Gemma lookup, Qwen mid/complex, DeepSeek R1 reasoning",
    ),
    "workstation_16gb": RecommendedStack(
        profile="workstation_16gb",
        models=("gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b"),
        description="12 GB stack + room for QAT Gemma 26B; add coder tags via models=",
    ),
    "workstation_24gb": RecommendedStack(
        profile="workstation_24gb",
        models=(
            "gemma4:e4b",
            "qwen3:8b",
            "qwen3:14b",
            "qwen3:30b-a3b",
            "deepseek-coder:6.7b",
        ),
        description="Full mixed ladder with MoE top and code specialist",
    ),
    "workstation_32gb": RecommendedStack(
        profile="workstation_32gb",
        models=(
            "gemma4:e4b",
            "qwen3:8b",
            "qwen3:14b",
            "qwen3:30b-a3b",
            "deepseek-coder:6.7b",
            "deepseek-r1:8b",
        ),
        description="5090 class: MoE + separate reasoning and code specialists",
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
    from split_stack.quantization import expand_models_for_quant

    return expand_models_for_quant(list(stack.models), profile_name, quant)


def assign_recommended_tiers(profile: str) -> TierMap:
    return assign_tiers(recommended_models(profile))
