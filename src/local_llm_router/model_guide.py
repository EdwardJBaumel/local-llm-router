"""Model guide: map agent hints and installed models to routing tiers."""

from __future__ import annotations

from dataclasses import dataclass

from local_llm_router.community_picks import (
    community_index_for_model,
    community_note_for_model,
    recommended_models_for_tier,
    vram_tier_for_profile,
)
from local_llm_router.hints import list_hints
from local_llm_router.model_registry import load_registry, resolve_discovered_models
from local_llm_router.routing import route_prompt
from local_llm_router.tiering import assign_tiers, describe_tiers

# Example prompts per hint — same spirit as compare POC steps.
HINT_EXAMPLES: dict[str, str] = {
    "lookup": "what is JWT in one sentence?",
    "explain": "compare session cookies vs JWT for a small SaaS API",
    "design": "design a webhook retry strategy with idempotency keys",
    "code": "refactor this auth module for unit tests",
    "reason": "prove this token expiry policy step by step",
}

TIER_LABELS: dict[str, str] = {
    "simple": "Simple — fast, cheap steps",
    "medium": "Medium — summarise and compare",
    "complex": "Complex — design and heavy generation",
    "reasoning": "Reasoning — proofs and step-by-step logic",
    "code": "Code — implement, refactor, debug",
}

FAMILY_BEST_FOR: dict[str, str] = {
    "gemma": "Lookup and quick answers; smallest Gemma tag in your stack",
    "qwen": "General spine — explain on 8B, design on 14B+",
    "llama": "Lightweight lookup on 1B/3B; mid tiers on 8B+",
    "phi": "Reasoning and careful step-by-step (especially phi4-reasoning)",
    "deepseek": "Reasoning (R1) or code (coder) specialists",
    "mistral": "Solid medium-tier general work",
    "starcoder": "Code-only slot when present",
}


@dataclass(frozen=True)
class HintRoute:
    hint_id: str
    label: str
    summary: str
    tier: str
    model: str
    example_prompt: str


@dataclass(frozen=True)
class ModelCard:
    name: str
    family: str | None
    weight: int
    vram_gb: int | None
    tier_slots: tuple[str, ...]
    hints: tuple[str, ...]
    best_for: str
    in_stack: bool
    vram_ok: bool
    community_note: str | None = None
    community_hints: tuple[str, ...] = ()
    installed: bool = True
    duplicate_locations: tuple[str, ...] = ()
    status: str = "installed"


@dataclass(frozen=True)
class ModelGuide:
    stack: tuple[str, ...]
    tiers: dict[str, str | None]
    tier_labels: dict[str, str]
    hint_routes: tuple[HintRoute, ...]
    models: tuple[ModelCard, ...]
    vram_tier: str | None = None
    audit: dict[str, object] | None = None
    missing_recommended: tuple[str, ...] = ()


def _tier_slots_for_model(name: str, tiers: dict[str, str | None]) -> list[str]:
    slots: list[str] = []
    for key, value in tiers.items():
        if value == name:
            slots.append(key)
    return slots


def _hints_for_model(name: str, hint_routes: tuple[HintRoute, ...]) -> list[str]:
    return [item.hint_id for item in hint_routes if item.model == name]


def _best_for_text(
    *,
    name: str,
    family: str | None,
    tier_slots: list[str],
    in_stack: bool,
    community_note: str | None,
    community_hints: tuple[str, ...],
    installed: bool,
) -> str:
    parts: list[str] = []
    if community_note:
        parts.append(community_note)
    elif community_hints:
        parts.append(f"Community pick for: {', '.join(community_hints)}")
    if not installed:
        return parts[0] if parts else "Recommended by community — not installed yet"

    lowered = name.lower()
    if "reasoning" in lowered or "deepseek-r1" in lowered:
        parts.append("Reasoning steps — proofs and step-by-step logic")
    elif any(token in lowered for token in ("coder", "codellama", "starcoder")):
        parts.append("Code steps — refactor, debug, implement")
    elif family and family in FAMILY_BEST_FOR and not parts:
        parts.append(FAMILY_BEST_FOR[family])

    if not in_stack:
        suffix = "Installed but not in your active stack"
        return f"{parts[0]} — {suffix}" if parts else suffix
    if "simple" in tier_slots:
        parts.append("Routed for lookup hints")
    elif "medium" in tier_slots and "complex" not in tier_slots:
        parts.append("Routed for explain hints")
    elif "complex" in tier_slots:
        parts.append("Routed for design/code hints")
    elif "reasoning" in tier_slots:
        parts.append("Routed for reason hints")
    return " · ".join(dict.fromkeys(p for p in parts if p))


def build_model_guide(
    stack: list[str],
    *,
    pool: list[str] | None = None,
    config_path: str | None = None,
    profile: str = "workstation_12gb",
) -> ModelGuide:
    """Build hint routes for the active stack and cards for all models in pool."""
    if not stack:
        raise ValueError("stack must contain at least one model")

    registry = load_registry(config_path)
    vram_tier = vram_tier_for_profile(profile, config_path=config_path)
    from local_llm_router.discovery import audit_model_folders, model_locations_by_tag

    locations = model_locations_by_tag()
    audit = audit_model_folders()
    recommended = recommended_models_for_tier(vram_tier=vram_tier, config_path=config_path)
    tiers_map = assign_tiers(stack, registry=registry)
    tiers = describe_tiers(tiers_map)

    hint_routes: list[HintRoute] = []
    for item in list_hints():
        hint_id = item["id"]
        example = HINT_EXAMPLES.get(hint_id, item["summary"])
        tier, model = route_prompt(example, tiers_map, hint=hint_id)
        hint_routes.append(
            HintRoute(
                hint_id=hint_id,
                label=item["label"],
                summary=item["summary"],
                tier=tier.value,
                model=model,
                example_prompt=example,
            )
        )
    hint_routes_tuple = tuple(hint_routes)

    catalog = pool if pool is not None else stack
    resolved = resolve_discovered_models(sorted(set(catalog)), registry=registry)
    stack_set = set(stack)
    seen_names: set[str] = set()

    full_tiers = describe_tiers(assign_tiers(list(catalog), registry=registry)) if len(catalog) >= 2 else tiers

    cards: list[ModelCard] = []
    for item in resolved:
        seen_names.add(item.name)
        in_stack = item.name in stack_set
        tier_slots = _tier_slots_for_model(item.name, tiers if in_stack else full_tiers)
        route_hints = _hints_for_model(item.name, hint_routes_tuple) if in_stack else []
        comm_hints = community_index_for_model(item.name, vram_tier=vram_tier, config_path=config_path)
        comm_note = community_note_for_model(item.name, vram_tier=vram_tier, config_path=config_path)
        locs = locations.get(item.name, ())
        cards.append(
            ModelCard(
                name=item.name,
                family=item.family,
                weight=item.weight,
                vram_gb=item.vram_gb,
                tier_slots=tuple(tier_slots),
                hints=tuple(route_hints),
                best_for=_best_for_text(
                    name=item.name,
                    family=item.family,
                    tier_slots=tier_slots,
                    in_stack=in_stack,
                    community_note=comm_note,
                    community_hints=comm_hints,
                    installed=True,
                ),
                in_stack=in_stack,
                vram_ok=item.vram_ok,
                community_note=comm_note,
                community_hints=comm_hints,
                installed=True,
                duplicate_locations=tuple(locs) if len(locs) > 1 else (),
                status="duplicate" if len(locs) > 1 else "installed",
            )
        )

    installed_lower = {name.lower() for name in seen_names}
    missing: list[str] = []
    for model_name, note in recommended.items():
        if model_name.lower() in installed_lower:
            continue
        if any(model_name.lower() in name or name.startswith(model_name.lower()) for name in installed_lower):
            continue
        missing.append(model_name)
        comm_hints = community_index_for_model(model_name, vram_tier=vram_tier, config_path=config_path)
        cards.append(
            ModelCard(
                name=model_name,
                family=model_name.split(":")[0],
                weight=0,
                vram_gb=None,
                tier_slots=(),
                hints=(),
                best_for=_best_for_text(
                    name=model_name,
                    family=model_name.split(":")[0],
                    tier_slots=[],
                    in_stack=False,
                    community_note=note,
                    community_hints=comm_hints,
                    installed=False,
                ),
                in_stack=False,
                vram_ok=True,
                community_note=note,
                community_hints=comm_hints,
                installed=False,
                status="recommended",
            )
        )

    cards.sort(
        key=lambda card: (
            card.status != "installed",
            card.status == "recommended",
            not card.in_stack,
            card.weight,
            card.name,
        )
    )

    return ModelGuide(
        stack=tuple(stack),
        tiers=tiers,
        tier_labels=dict(TIER_LABELS),
        hint_routes=hint_routes_tuple,
        models=tuple(cards),
        vram_tier=vram_tier,
        audit=audit,
        missing_recommended=tuple(missing),
    )
