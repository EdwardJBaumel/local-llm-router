"""Default model stacks for POC demos and compare benchmarks."""

from __future__ import annotations

from dataclasses import dataclass

from split_stack.community_picks import focus_stack, vram_tier_for_profile
from split_stack.discovery import list_model_inventory
from split_stack.presets import recommended_models

DEFAULT_POC_STACK = ["gemma4:e4b", "qwen3:8b", "qwen3:14b"]
QWEN_ONLY_STACK = ["qwen3:4b", "qwen3:8b", "qwen3:14b"]


@dataclass(frozen=True)
class StackPreset:
    id: str
    label: str
    models: tuple[str, ...]
    description: str


STACK_PRESETS: tuple[StackPreset, ...] = (
    StackPreset(
        id="mixed_12gb",
        label="Mixed 12 GB (Gemma + Qwen)",
        models=tuple(DEFAULT_POC_STACK),
        description="Gemma lookup, Qwen 8B medium, Qwen 14B complex",
    ),
    StackPreset(
        id="qwen_only",
        label="Qwen only (4B / 8B / 14B)",
        models=tuple(QWEN_ONLY_STACK),
        description="Single-family ladder",
    ),
    StackPreset(
        id="recommended_12gb",
        label="Full 12 GB specialist",
        models=tuple(recommended_models("workstation_12gb")),
        description="Gemma + Qwen + DeepSeek R1 for reasoning",
    ),
    StackPreset(
        id="community_agentic",
        label="Reddit agentic (M tier)",
        models=tuple(),
        description="r/LocalLLaMA Apr 2026 — Gemma lookup + Qwen spine for agent loops",
    ),
    StackPreset(
        id="from_inventory",
        label="From your Ollama (auto ladder)",
        models=tuple(),
        description="Picks small/mid/large tags from API + disk manifests",
    ),
)


def list_stack_presets() -> tuple[StackPreset, ...]:
    return STACK_PRESETS


def models_for_preset(
    preset_id: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    profile: str = "workstation_12gb",
) -> list[str]:
    if preset_id == "from_inventory":
        inventory = list_model_inventory(base_url=base_url)
        if inventory.suggested_stack:
            return list(inventory.suggested_stack)
        return list(DEFAULT_POC_STACK)
    if preset_id == "community_agentic":
        tier = vram_tier_for_profile(profile)
        stack = focus_stack("agentic", vram_tier=tier)
        if stack and stack.models:
            return list(stack.models)
        return list(DEFAULT_POC_STACK)
    for item in STACK_PRESETS:
        if item.id == preset_id:
            return list(item.models)
    valid = ", ".join(item.id for item in STACK_PRESETS)
    raise ValueError(f"Unknown stack preset '{preset_id}'. Valid: {valid}")


def available_model_pool(
    *,
    base_url: str = "http://127.0.0.1:11434",
    source: str = "both",
) -> tuple[list[str], str | None]:
    """Return model names from Ollama API, disk manifests, or both."""
    inventory = list_model_inventory(base_url=base_url)
    if source == "api":
        pool = list(inventory.api_models)
    elif source == "disk":
        pool = list(inventory.disk_models)
    else:
        pool = sorted(set(inventory.api_models) | set(inventory.disk_models))
    return pool, inventory.note


def resolve_installed_stack(
    installed: list[str],
    *,
    preset_id: str = "mixed_12gb",
    base_url: str = "http://127.0.0.1:11434",
) -> tuple[list[str], str | None]:
    """Pick preset models that exist in the installed pool; warn when falling back."""
    desired = models_for_preset(preset_id, base_url=base_url)
    installed_set = set(installed)
    matched = [name for name in desired if name in installed_set]
    if len(matched) >= 2:
        return matched, None

    if installed:
        from split_stack.model_registry import load_registry, model_weight

        registry = load_registry()
        ranked = sorted(installed, key=lambda name: model_weight(name, registry))
        if len(ranked) >= 2:
            warning = (
                f"Preset '{preset_id}' not fully available ({', '.join(desired)}). "
                f"Using: {', '.join(ranked)}"
            )
            return ranked, warning
        warning = (
            f"Preset '{preset_id}' not fully available. "
            f"Using only {ranked[0]} — need 2+ models for compare spread."
        )
        return ranked, warning

    return desired, f"Using preset list (not verified): {', '.join(desired)}"
