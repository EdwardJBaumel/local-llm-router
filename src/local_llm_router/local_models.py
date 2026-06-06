from __future__ import annotations

from local_llm_router.discovery import discover_models, discover_models_from_disk, list_model_inventory
from local_llm_router.model_registry import ResolvedModel, load_registry, resolve_discovered_models
from local_llm_router.tiering import assign_tiers


def list_local_models(
    *,
    base_url: str = "http://127.0.0.1:11434",
    config_path: str | None = None,
    profile: str | None = None,
    only_vram_ok: bool = False,
    include_disk: bool = False,
    quant_mode: str | None = None,
) -> tuple[list[ResolvedModel], str | None]:
    registry = load_registry(config_path, profile=profile)
    discovered = discover_models(base_url=base_url)
    note: str | None = None
    if include_disk:
        inventory = list_model_inventory(base_url=base_url)
        discovered = sorted(set(discovered) | set(inventory.disk_models))
        note = inventory.note
    effective_filter = only_vram_ok and registry.apply_vram_filter
    resolved = resolve_discovered_models(
        discovered,
        registry=registry,
        only_vram_ok=effective_filter,
        quant_mode=quant_mode,
    )
    warning = None
    if effective_filter and len(resolved) < 2:
        warning = (
            "Fewer than two models fit assumed_vram_gb="
            f"{registry.assumed_vram_gb}. Add smaller models, pick a larger workstation profile, "
            "or set deployment_profile to datacenter with a custom catalog."
        )
    if note and not warning:
        warning = note
    elif note and warning:
        warning = f"{warning} {note}"
    return resolved, warning


def assign_tiers_from_local(
    *,
    base_url: str = "http://127.0.0.1:11434",
    config_path: str | None = None,
    profile: str | None = None,
    only_vram_ok: bool = True,
    quant_mode: str | None = None,
):
    models, warning = list_local_models(
        base_url=base_url,
        config_path=config_path,
        profile=profile,
        only_vram_ok=only_vram_ok,
        quant_mode=quant_mode,
    )
    if not models:
        raise RuntimeError("No models available after discovery and VRAM filter")
    tiers = assign_tiers([item.name for item in models])
    return tiers, models, warning
