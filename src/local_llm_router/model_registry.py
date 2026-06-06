from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ASSUMED_VRAM_GB = 12
DEFAULT_DEPLOYMENT_PROFILE = "workstation_12gb"


@dataclass(frozen=True)
class DeploymentProfileSpec:
    name: str
    assumed_vram_gb: int | None
    apply_vram_filter: bool
    description: str


DEPLOYMENT_PROFILES: dict[str, DeploymentProfileSpec] = {
    "workstation_8gb": DeploymentProfileSpec(
        name="workstation_8gb",
        assumed_vram_gb=8,
        apply_vram_filter=True,
        description="8 GB GPU workstation preset",
    ),
    "workstation_12gb": DeploymentProfileSpec(
        name="workstation_12gb",
        assumed_vram_gb=12,
        apply_vram_filter=True,
        description="12 GB GPU workstation preset (default)",
    ),
    "workstation_16gb": DeploymentProfileSpec(
        name="workstation_16gb",
        assumed_vram_gb=16,
        apply_vram_filter=True,
        description="16 GB GPU workstation preset",
    ),
    "workstation_24gb": DeploymentProfileSpec(
        name="workstation_24gb",
        assumed_vram_gb=24,
        apply_vram_filter=True,
        description="24 GB GPU workstation preset (4090, 3090 class)",
    ),
    "workstation_32gb": DeploymentProfileSpec(
        name="workstation_32gb",
        assumed_vram_gb=32,
        apply_vram_filter=True,
        description="32 GB GPU workstation preset (5090 class; top single-GPU tier)",
    ),
    "datacenter": DeploymentProfileSpec(
        name="datacenter",
        assumed_vram_gb=None,
        apply_vram_filter=False,
        description="Private inference fleet; custom model catalog, no VRAM filter",
    ),
}

_PROFILE_ALIASES: dict[str, str] = {
    "workstation": DEFAULT_DEPLOYMENT_PROFILE,
    "8gb": "workstation_8gb",
    "12gb": "workstation_12gb",
    "16gb": "workstation_16gb",
    "24gb": "workstation_24gb",
    "32gb": "workstation_32gb",
}

_BUILTIN_RAW: list[dict[str, object]] = [
    {"match": "gemma4:e4b", "weight": 4000, "vram_gb": 4, "family": "gemma"},
    {"match": "gemma4:12b", "weight": 12000, "vram_gb": 10, "family": "gemma"},
    {"match": "gemma4:26b-a4b", "weight": 26000, "vram_gb": 20, "family": "gemma"},
    {"match": "gemma4:26b", "weight": 26000, "vram_gb": 22, "family": "gemma"},
    {"match": "gemma4:31b", "weight": 31000, "vram_gb": 28, "family": "gemma"},
    {"match": "gemma3:4b", "weight": 4000, "vram_gb": 4, "family": "gemma"},
    {"match": "gemma3:12b", "weight": 12000, "vram_gb": 10, "family": "gemma"},
    {"match": "qwen3:4b", "weight": 4000, "vram_gb": 4, "family": "qwen"},
    {"match": "qwen3:8b", "weight": 8000, "vram_gb": 6, "family": "qwen"},
    {"match": "qwen3:14b", "weight": 14000, "vram_gb": 10, "family": "qwen"},
    {"match": "qwen3:30b", "weight": 30000, "vram_gb": 20, "family": "qwen"},
    {"match": "qwen3:30b-a3b", "weight": 30000, "vram_gb": 20, "family": "qwen"},
    {"match": "llama3.2:1b", "weight": 1000, "vram_gb": 2, "family": "llama"},
    {"match": "llama3.2:3b", "weight": 3000, "vram_gb": 3, "family": "llama"},
    {"match": "llama3.1:8b", "weight": 8000, "vram_gb": 6, "family": "llama"},
    {"match": "llama3.1:70b", "weight": 70000, "vram_gb": 48, "family": "llama"},
    {"match": "mistral:7b", "weight": 7000, "vram_gb": 5, "family": "mistral"},
    {"match": "mistral-nemo", "weight": 12000, "vram_gb": 8, "family": "mistral"},
    {"match": "phi3:mini", "weight": 3800, "vram_gb": 4, "family": "phi"},
    {"match": "phi4", "weight": 14000, "vram_gb": 10, "family": "phi"},
    {"match": "phi4-reasoning", "weight": 14000, "vram_gb": 10, "family": "phi"},
    {"match": "deepseek-coder:6.7b", "weight": 7000, "vram_gb": 6, "family": "deepseek"},
    {"match": "deepseek-r1", "weight": 14000, "vram_gb": 10, "family": "deepseek"},
    {"match": "deepseek-coder", "weight": 7000, "vram_gb": 6, "family": "deepseek"},
    {"match": "codellama", "weight": 7000, "vram_gb": 6, "family": "llama"},
    {"match": "starcoder2", "weight": 7000, "vram_gb": 6, "family": "starcoder"},
    {"match": ":e4b", "weight": 4000, "vram_gb": 4, "family": "gemma"},
    {"match": ":e2b", "weight": 2000, "vram_gb": 3, "family": "gemma"},
]


@dataclass(frozen=True)
class ModelEntry:
    match: str
    weight: int
    vram_gb: int | None = None
    family: str | None = None


@dataclass(frozen=True)
class ModelRegistry:
    profile: str
    assumed_vram_gb: int | None
    apply_vram_filter: bool
    entries: tuple[ModelEntry, ...]


@dataclass(frozen=True)
class ResolvedModel:
    name: str
    weight: int
    vram_gb: int | None
    family: str | None
    vram_ok: bool
    source: str
    quant_mode: str | None = None


def _entries_from_raw(raw: list[dict[str, object]]) -> tuple[ModelEntry, ...]:
    return tuple(
        ModelEntry(
            match=str(item["match"]),
            weight=int(item["weight"]),  # type: ignore[arg-type]
            vram_gb=int(item["vram_gb"]) if item.get("vram_gb") is not None else None,
            family=str(item["family"]) if item.get("family") else None,
        )
        for item in raw
    )


def normalize_deployment_profile(name: str | None) -> str:
    if not name:
        return DEFAULT_DEPLOYMENT_PROFILE
    lowered = name.strip().lower()
    if lowered in DEPLOYMENT_PROFILES:
        return lowered
    if lowered in _PROFILE_ALIASES:
        return _PROFILE_ALIASES[lowered]
    valid = ", ".join(sorted(DEPLOYMENT_PROFILES))
    raise ValueError(f"Unknown deployment profile '{name}'. Valid profiles: {valid}")


def list_deployment_profiles() -> tuple[DeploymentProfileSpec, ...]:
    return tuple(DEPLOYMENT_PROFILES[name] for name in sorted(DEPLOYMENT_PROFILES))


def _default_registry() -> ModelRegistry:
    spec = DEPLOYMENT_PROFILES[DEFAULT_DEPLOYMENT_PROFILE]
    return ModelRegistry(
        profile=spec.name,
        assumed_vram_gb=spec.assumed_vram_gb,
        apply_vram_filter=spec.apply_vram_filter,
        entries=_entries_from_raw(_BUILTIN_RAW),
    )


def _registry_from_payload(
    payload: dict[str, object],
    *,
    profile_override: str | None = None,
) -> ModelRegistry:
    profile_name = normalize_deployment_profile(
        profile_override
        or str(payload.get("deployment_profile") or payload.get("profile") or "")
        or None
    )
    spec = DEPLOYMENT_PROFILES[profile_name]
    entries_raw = payload.get("models")
    entries = _entries_from_raw(list(entries_raw)) if entries_raw else _entries_from_raw(_BUILTIN_RAW)
    if spec.apply_vram_filter:
        if profile_override:
            assumed_vram_gb = spec.assumed_vram_gb
        else:
            assumed = payload.get("assumed_vram_gb")
            assumed_vram_gb = int(assumed) if assumed is not None else spec.assumed_vram_gb
    else:
        assumed_vram_gb = None
    return ModelRegistry(
        profile=profile_name,
        assumed_vram_gb=assumed_vram_gb,
        apply_vram_filter=spec.apply_vram_filter,
        entries=entries,
    )


def config_search_paths(explicit: str | None = None) -> list[Path]:
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit))
    env_path = os.environ.get("LOCAL_LLM_ROUTER_MODELS_CONFIG")
    if env_path:
        paths.append(Path(env_path))
    paths.extend(
        [
            Path.cwd() / "local-llm-router.models.json",
            Path.home() / ".config" / "local-llm-router" / "models.json",
        ]
    )
    return paths


def load_registry(
    config_path: str | None = None,
    *,
    profile: str | None = None,
) -> ModelRegistry:
    for path in config_search_paths(config_path):
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            return _registry_from_payload(payload, profile_override=profile)
    if profile:
        spec = DEPLOYMENT_PROFILES[normalize_deployment_profile(profile)]
        base = _default_registry()
        return ModelRegistry(
            profile=spec.name,
            assumed_vram_gb=spec.assumed_vram_gb,
            apply_vram_filter=spec.apply_vram_filter,
            entries=base.entries,
        )
    return _default_registry()


def _heuristic_weight(name: str) -> int:
    lowered = name.lower()
    match = re.search(r":(\d+)b", lowered)
    if match:
        return int(match.group(1)) * 1000
    match = re.search(r":e(\d+)b", lowered)
    if match:
        return int(match.group(1)) * 1000
    if "70b" in lowered:
        return 70000
    if "30b" in lowered or "32b" in lowered or "34b" in lowered:
        return 30000
    return 1000


def infer_model_profile(
    name: str,
    registry: ModelRegistry | None = None,
    *,
    quant_mode: str | None = None,
) -> ResolvedModel:
    reg = registry or _default_registry()
    lowered = name.lower()
    best: ModelEntry | None = None
    best_len = -1
    for entry in reg.entries:
        token = entry.match.lower()
        if token in lowered and len(token) > best_len:
            best = entry
            best_len = len(token)
    if best is not None:
        vram_gb = best.vram_gb
        source = "registry"
        weight = best.weight
        family = best.family
    else:
        source = "heuristic"
        weight = _heuristic_weight(name)
        family = _guess_family(name)
        vram_gb = max(3, weight // 1000)
    from local_llm_router.quantization import adjust_vram_for_quant, normalize_quant_mode

    mode = normalize_quant_mode(quant_mode)
    effective_vram = adjust_vram_for_quant(name, vram_gb, mode)
    if not reg.apply_vram_filter or reg.assumed_vram_gb is None:
        vram_ok = True
    else:
        vram_ok = effective_vram is None or effective_vram <= reg.assumed_vram_gb
    return ResolvedModel(
        name=name,
        weight=weight,
        vram_gb=effective_vram,
        family=family,
        vram_ok=vram_ok,
        source=source,
        quant_mode=mode if mode != "default" else None,
    )


def _guess_family(name: str) -> str | None:
    lowered = name.lower()
    for family in ("qwen", "gemma", "llama", "mistral", "phi", "deepseek"):
        if family in lowered:
            return family
    return None


def resolve_discovered_models(
    model_names: list[str],
    *,
    registry: ModelRegistry | None = None,
    only_vram_ok: bool = False,
    quant_mode: str | None = None,
) -> list[ResolvedModel]:
    reg = registry or _default_registry()
    resolved = [infer_model_profile(name, reg, quant_mode=quant_mode) for name in model_names]
    if only_vram_ok:
        resolved = [item for item in resolved if item.vram_ok]
    return sorted(resolved, key=lambda item: item.weight)


def model_weight(name: str, registry: ModelRegistry | None = None) -> int:
    return infer_model_profile(name, registry).weight
