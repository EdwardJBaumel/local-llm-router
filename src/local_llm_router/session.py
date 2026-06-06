"""Minimal session: set VRAM once, route every call."""

from __future__ import annotations

import os
from dataclasses import dataclass

from local_llm_router.model_registry import normalize_deployment_profile
from local_llm_router.models import ComplexityTier, RouteDecision, TierMap
from local_llm_router.presets import recommended_models
from local_llm_router.routing import explain_route, route_prompt
from local_llm_router.tiering import assign_tiers, describe_tiers
from local_llm_router.validation import validate_tier_map


@dataclass(frozen=True)
class Session:
    profile: str
    vram_gb: int | None
    quant: str
    models: tuple[str, ...]
    tiers: TierMap
    warnings: tuple[str, ...] = ()
    note: str | None = None


_session: Session | None = None


def profile_for_vram_gb(vram_gb: int) -> str:
    """Map discrete GPU VRAM to a workstation deployment profile."""
    if vram_gb <= 8:
        return "workstation_8gb"
    if vram_gb <= 12:
        return "workstation_12gb"
    if vram_gb <= 16:
        return "workstation_16gb"
    if vram_gb <= 24:
        return "workstation_24gb"
    if vram_gb <= 32:
        return "workstation_32gb"
    return "datacenter"


def _vram_from_env() -> int | None:
    raw = (
        os.environ.get("local_llm_router_VRAM_GB", "")
        or os.environ.get("SPLIT_STACK_VRAM_GB", "")  # deprecated alias
    ).strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _profile_from_env() -> str | None:
    raw = (
        os.environ.get("local_llm_router_PROFILE", "")
        or os.environ.get("SPLIT_STACK_PROFILE", "")  # deprecated alias
    ).strip()
    return raw or None


def default_profile_from_env(*, fallback: str = "workstation_12gb") -> str:
    """Profile from local_llm_router_PROFILE or local_llm_router_VRAM_GB, else fallback."""
    profile = _profile_from_env()
    if profile:
        return normalize_deployment_profile(profile)
    vram = _vram_from_env()
    if vram is not None:
        return profile_for_vram_gb(vram)
    return fallback


def _quant_from_env() -> str | None:
    from local_llm_router.quantization import quant_from_env

    return quant_from_env()


def _resolve_models(
    profile: str,
    models: list[str] | None,
    *,
    quant: str | None = None,
) -> tuple[list[str], str | None]:
    if models:
        return models, None

    from local_llm_router.quantization import normalize_quant_mode

    desired = recommended_models(profile, quant=quant)
    note: str | None = None
    mode = normalize_quant_mode(quant)
    if mode == "qat" and len(desired) > len(recommended_models(profile)):
        note = "QAT stack: added Gemma 4 models that fit at int4 runtime sizes."
    try:
        from local_llm_router.discovery import discover_models_from_disk

        disk = discover_models_from_disk()
    except Exception:
        disk = []

    if disk:
        matched = [name for name in desired if name in disk]
        if len(matched) >= 2:
            return matched, None
        if len(disk) >= 2:
            from local_llm_router.model_registry import load_registry, model_weight

            registry = load_registry(profile=profile)
            ranked = sorted(disk, key=lambda name: model_weight(name, registry))
            note = (
                f"Recommended stack not fully installed ({', '.join(desired)}). "
                f"Using: {', '.join(ranked[:3])}"
            )
            return ranked[:3], note
        note = f"Using installed models only: {', '.join(disk)}"
        return disk, note

    return desired, "Using recommended stack (not verified against disk)."


def configure(
    *,
    vram_gb: int | None = None,
    profile: str | None = None,
    models: list[str] | None = None,
    tiers: TierMap | None = None,
    quant: str | None = None,
) -> Session:
    """Set the default profile and tier map for ``route()`` and ``explain()``.

    Progressive control:
    - ``configure(vram_gb=16)`` — preset profile and recommended models
    - ``configure(..., models=[...])`` — explicit model list, auto tier ladder
    - ``configure(..., models=[...], tiers=...)`` — explicit ladder (power users)
    """
    global _session
    from local_llm_router.quantization import normalize_quant_mode

    if quant is None:
        quant = _quant_from_env()
    quant_mode = normalize_quant_mode(quant)

    if profile is None:
        profile = _profile_from_env()
    if profile is None:
        if vram_gb is None:
            vram_gb = _vram_from_env()
        if vram_gb is None:
            raise ValueError(
                "Pass vram_gb=16 (or profile='workstation_16gb'), "
                "or set local_llm_router_VRAM_GB / local_llm_router_PROFILE."
            )
        profile = profile_for_vram_gb(vram_gb)
    else:
        profile = normalize_deployment_profile(profile)
        if vram_gb is None:
            vram_gb = _vram_from_env()

    resolved_models, note = _resolve_models(profile, models, quant=quant_mode)
    if not resolved_models:
        raise ValueError(f"No models for profile {profile}")

    if tiers is not None:
        tier_map = tiers
        if models is not None:
            unknown = [
                name
                for name in (
                    tier_map.simple,
                    tier_map.medium,
                    tier_map.complex,
                    tier_map.reasoning,
                    tier_map.code,
                )
                if name and name not in resolved_models
            ]
            if unknown:
                raise ValueError(
                    f"tiers= references models not in models=: {', '.join(sorted(set(unknown)))}"
                )
    else:
        tier_map = assign_tiers(resolved_models)
    warnings = tuple(validate_tier_map(tier_map, resolved_models, profile=profile))
    _session = Session(
        profile=profile,
        vram_gb=vram_gb,
        quant=quant_mode,
        models=tuple(resolved_models),
        tiers=tier_map,
        warnings=warnings,
        note=note,
    )
    return _session


def get_session() -> Session | None:
    return _session


def session_warnings() -> tuple[str, ...]:
    """Warnings from the last ``configure()`` (empty if none)."""
    session = _session
    return session.warnings if session else ()


def _ensure_session() -> Session:
    session = _session
    if session is None:
        if _vram_from_env() is not None or _profile_from_env() is not None:
            configure()
            session = _session
        else:
            raise RuntimeError(
                "local_llm_router.configure(vram_gb=16) first, or set local_llm_router_VRAM_GB."
            )
    assert session is not None
    return session


def route(
    prompt: str,
    *,
    hint: str | None = None,
    mode: str | None = None,
) -> tuple[ComplexityTier, str]:
    """Route one prompt using the configured session. Call ``configure()`` first."""
    session = _ensure_session()
    return route_prompt(prompt, session.tiers, hint=hint, mode=mode)


def explain(
    prompt: str,
    *,
    hint: str | None = None,
    mode: str | None = None,
) -> RouteDecision:
    """Route with a full decision trace (logging, CLI, tests)."""
    session = _ensure_session()
    return explain_route(prompt, session.tiers, hint=hint, mode=mode)


def route_turn(prompt: str, *, mode: str | None = None) -> tuple[ComplexityTier, str]:
    """Alias for ``route(prompt, mode=mode)`` — one turn in chat or agent mode."""
    return route(prompt, mode=mode)


def describe_session() -> dict[str, object]:
    """Snapshot of the active session for logs and ``llm-router explain`` without a prompt."""
    session = get_session()
    if session is None:
        return {"configured": False}
    return {
        "configured": True,
        "profile": session.profile,
        "vram_gb": session.vram_gb,
        "quant": session.quant,
        "models": list(session.models),
        "tiers": describe_tiers(session.tiers),
        "warnings": list(session.warnings),
        "note": session.note,
    }


def reset_session_for_tests() -> None:
    global _session
    _session = None
