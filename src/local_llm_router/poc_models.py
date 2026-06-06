"""Workstation stack helpers for demos and compare POC."""

from __future__ import annotations

from dataclasses import dataclass

from local_llm_router.discovery import list_model_inventory
from local_llm_router.presets import RECOMMENDED_STACKS, recommended_models
from local_llm_router.quantization import QAT_STACK_ADDITIONS, normalize_quant_mode
from local_llm_router.session import profile_for_vram_gb

DEFAULT_POC_STACK = ["gemma4:e4b", "qwen3.5:9b", "qwen3:14b"]

VRAM_OPTIONS: tuple[tuple[int, str], ...] = (
    (8, "8 GB"),
    (12, "12 GB"),
    (16, "16 GB"),
    (24, "24 GB"),
    (32, "32 GB"),
)

QUANT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("default", "Default (PTQ)"),
    ("qat", "Gemma QAT (int4)"),
    ("qat_mobile", "Gemma mobile QAT"),
    ("bf16", "BF16 (full size)"),
)

_PRESET_VRAM_ALIASES: dict[str, int] = {
    "mixed_12gb": 12,
    "mixed_16gb": 16,
    "qwen_only": 12,
    "recommended_12gb": 12,
    "from_inventory": 0,
}


@dataclass(frozen=True)
class WorkstationStack:
    vram_gb: int
    profile: str
    quant: str
    models: tuple[str, ...]
    description: str
    notes: tuple[str, ...]


def list_vram_options() -> tuple[tuple[int, str], ...]:
    return VRAM_OPTIONS


def list_quant_options() -> tuple[tuple[str, str], ...]:
    return QUANT_OPTIONS


def recommended_stack_for_vram(
    vram_gb: int,
    *,
    quant: str | None = None,
) -> WorkstationStack:
    profile = profile_for_vram_gb(vram_gb)
    stack = RECOMMENDED_STACKS[profile]
    quant_mode = normalize_quant_mode(quant)
    models = recommended_models(profile, quant=quant_mode)
    notes: list[str] = []
    if quant_mode == "qat":
        extras = QAT_STACK_ADDITIONS.get(profile, ())
        if extras:
            notes.append(
                f"QAT adds {', '.join(extras)} on {vram_gb} GB — Gemma-only int4 runtime sizes."
            )
    elif quant_mode == "bf16":
        notes.append("BF16 uses full Gemma pull sizes — prefer 24 GB+ or datacenter.")
    return WorkstationStack(
        vram_gb=vram_gb,
        profile=profile,
        quant=quant_mode,
        models=tuple(models),
        description=stack.description,
        notes=tuple(notes),
    )


def models_for_preset(
    preset_id: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    profile: str | None = None,
    quant: str | None = None,
) -> list[str]:
    if preset_id == "from_inventory":
        inventory = list_model_inventory(base_url=base_url)
        if inventory.suggested_stack:
            return list(inventory.suggested_stack)
        return list(DEFAULT_POC_STACK)
    if preset_id == "qwen_only":
        return ["qwen3:4b", "qwen3:8b", "qwen3:14b"]
    if preset_id == "community_agentic":
        from local_llm_router.community_picks import focus_stack, vram_tier_for_profile

        tier = vram_tier_for_profile(profile or "workstation_12gb")
        focus = focus_stack("agentic", vram_tier=tier)
        if focus and focus.models:
            return list(focus.models)
        return list(DEFAULT_POC_STACK)
    vram = _PRESET_VRAM_ALIASES.get(preset_id)
    if vram:
        return list(recommended_stack_for_vram(vram, quant=quant).models)
    raise ValueError(f"Unknown stack preset '{preset_id}'.")


def available_model_pool(
    *,
    base_url: str = "http://127.0.0.1:11434",
    source: str = "both",
) -> tuple[list[str], str | None]:
    inventory = list_model_inventory(base_url=base_url)
    if source == "api":
        pool = list(inventory.api_models)
    elif source == "disk":
        pool = list(inventory.disk_models)
    else:
        pool = sorted(set(inventory.api_models) | set(inventory.disk_models))
    return pool, inventory.note


def resolve_stack_against_pool(
    desired: list[str],
    installed: list[str],
) -> tuple[list[str], list[str], str | None]:
    installed_set = set(installed)
    matched = [name for name in desired if name in installed_set]
    missing = [name for name in desired if name not in installed_set]
    if len(matched) >= 2:
        return matched, missing, None

    if installed:
        from local_llm_router.model_registry import load_registry, model_weight

        registry = load_registry()
        ranked = sorted(installed, key=lambda name: model_weight(name, registry))
        if len(ranked) >= 2:
            warning = (
                f"Recommended stack not fully installed ({', '.join(desired)}). "
                f"Using: {', '.join(ranked)}"
            )
            return ranked, missing, warning
        warning = (
            f"Recommended stack not fully installed. "
            f"Using only {ranked[0]} — need 2+ models for routing spread."
        )
        return ranked, missing, warning

    return desired, missing, f"Using recommended list (not verified against disk): {', '.join(desired)}"


def resolve_installed_stack(
    installed: list[str],
    *,
    preset_id: str = "mixed_12gb",
    base_url: str = "http://127.0.0.1:11434",
    vram_gb: int | None = None,
    quant: str | None = None,
    models: list[str] | None = None,
) -> tuple[list[str], str | None]:
    if models:
        desired = models
    elif vram_gb is not None:
        desired = list(recommended_stack_for_vram(vram_gb, quant=quant).models)
    else:
        desired = models_for_preset(preset_id, base_url=base_url, quant=quant)
    resolved, _missing, warning = resolve_stack_against_pool(desired, installed)
    return resolved, warning


def stack_payload(
    *,
    vram_gb: int = 16,
    quant: str | None = "qat",
    base_url: str = "http://127.0.0.1:11434",
    source: str = "both",
    models_override: list[str] | None = None,
) -> dict[str, object]:
    stack = recommended_stack_for_vram(vram_gb, quant=quant)
    desired = list(models_override) if models_override else list(stack.models)
    pool, inventory_note = available_model_pool(base_url=base_url, source=source)
    resolved, missing, warning = resolve_stack_against_pool(desired, pool)
    return {
        "ready": True,
        "vram_gb": vram_gb,
        "profile": stack.profile,
        "quant": stack.quant,
        "description": stack.description,
        "notes": list(stack.notes),
        "models": desired,
        "resolved_models": resolved,
        "missing_models": missing,
        "warning": warning,
        "inventory_note": inventory_note,
        "pool_size": len(pool),
    }
