from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_CONFIGURED_MODELS_DIR: Path | None = None


def configure_models_dir(path: str | Path | None) -> None:
    """Pin an Ollama models directory for discovery (used by demo server)."""
    global _CONFIGURED_MODELS_DIR
    if not path:
        _CONFIGURED_MODELS_DIR = None
        return
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        _CONFIGURED_MODELS_DIR = None
        return
    _CONFIGURED_MODELS_DIR = resolved if resolved.is_dir() else None


def default_models_dir() -> Path | None:
    """First existing Ollama models folder from env and common dev layouts."""
    candidates: list[Path] = []
    if _CONFIGURED_MODELS_DIR is not None:
        candidates.append(_CONFIGURED_MODELS_DIR)

    for key in ("SPLIT_STACK_OLLAMA_MODELS", "OLLAMA_MODELS"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidates.append(Path(raw))

    profile = os.environ.get("USERPROFILE", "").strip()
    if profile:
        candidates.append(Path(profile) / "dev" / "Tools" / ".ollama" / "models")

    home = Path.home()
    candidates.extend(
        [
            home / "dev" / "Tools" / ".ollama" / "models",
            home / ".ollama" / "models",
        ]
    )

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        library = resolved / "manifests" / "registry.ollama.ai" / "library"
        if library.is_dir():
            return resolved
    return None


@dataclass(frozen=True)
class ModelInventory:
    api_models: tuple[str, ...]
    disk_models: tuple[str, ...]
    manifest_roots: tuple[str, ...]
    suggested_stack: tuple[str, ...]
    note: str | None = None


def manifest_search_paths(extra_root: str | Path | None = None) -> list[Path]:
    """Candidate Ollama model directories (OLLAMA_MODELS, home, common dev layout)."""
    seen: set[Path] = set()
    ordered: list[Path] = []

    def add(path: Path | None) -> None:
        if path is None:
            return
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            return
        if resolved in seen or not resolved.is_dir():
            return
        seen.add(resolved)
        ordered.append(resolved)

    env_models = os.environ.get("OLLAMA_MODELS", "").strip()
    if env_models:
        add(Path(env_models))

    split_stack_models = os.environ.get("SPLIT_STACK_OLLAMA_MODELS", "").strip()
    if split_stack_models:
        add(Path(split_stack_models))

    if _CONFIGURED_MODELS_DIR is not None:
        add(_CONFIGURED_MODELS_DIR)

    profile = os.environ.get("USERPROFILE", "").strip()
    if profile:
        add(Path(profile) / "dev" / "Tools" / ".ollama" / "models")

    if extra_root:
        add(Path(extra_root))

    home = Path.home()
    add(home / ".ollama" / "models")
    add(home / "dev" / "Tools" / ".ollama" / "models")

    return ordered


def discover_models_from_disk(
    *,
    manifests_root: Path | str | None = None,
) -> list[str]:
    """List model tags from on-disk Ollama manifests (family/tag → family:tag)."""
    roots = manifest_search_paths(extra_root=Path(manifests_root) if manifests_root else None)
    found: set[str] = set()

    for root in roots:
        library = root / "manifests" / "registry.ollama.ai" / "library"
        if not library.is_dir():
            continue
        for family_dir in library.iterdir():
            if not family_dir.is_dir():
                continue
            for tag_path in family_dir.iterdir():
                if tag_path.is_file():
                    found.add(f"{family_dir.name}:{tag_path.name}")

    return sorted(found)


def discover_models(base_url: str = "http://127.0.0.1:11434") -> list[str]:
    """Models the running Ollama server reports via /api/tags."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "discover_models requires optional dependency: pip install split-stack[ollama]"
        ) from exc

    url = f"{base_url.rstrip('/')}/api/tags"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    payload = response.json() or {}
    models = [item.get("name", "") for item in payload.get("models", [])]
    return [model for model in models if model]


def _suggest_stack_from_pool(model_names: list[str], *, count: int = 3) -> list[str]:
    if not model_names:
        return []
    if len(model_names) <= count:
        return list(model_names)

    from split_stack.model_registry import load_registry, model_weight

    registry = load_registry()
    ranked = sorted(model_names, key=lambda name: model_weight(name, registry))
    if count == 3 and len(ranked) >= 3:
        return [ranked[0], ranked[len(ranked) // 2], ranked[-1]]
    return ranked[:count]


def list_model_inventory(
    *,
    base_url: str = "http://127.0.0.1:11434",
    manifests_root: Path | str | None = None,
) -> ModelInventory:
    """Merge Ollama API tags with on-disk manifest scan."""
    roots = manifest_search_paths(extra_root=Path(manifests_root) if manifests_root else None)
    api_models: list[str] = []
    api_error: str | None = None
    try:
        api_models = discover_models(base_url=base_url)
    except Exception as exc:
        api_error = str(exc)

    disk_models = discover_models_from_disk(manifests_root=manifests_root)
    pool = sorted(set(api_models) | set(disk_models))
    suggested = _suggest_stack_from_pool(pool, count=3)

    note_parts: list[str] = []
    if api_error:
        note_parts.append(f"Ollama API unreachable: {api_error}")
    elif len(api_models) < len(disk_models):
        note_parts.append(
            f"Ollama API lists {len(api_models)} model(s) but disk has {len(disk_models)}. "
            "Point Ollama at your model folder (OLLAMA_MODELS) or use disk models in the demo."
        )
    if not roots:
        note_parts.append("No Ollama model directories found on disk.")
    if note_parts:
        note = " ".join(note_parts)
    else:
        note = None

    return ModelInventory(
        api_models=tuple(api_models),
        disk_models=tuple(disk_models),
        manifest_roots=tuple(str(path) for path in roots),
        suggested_stack=tuple(suggested),
        note=note,
    )


def model_locations_by_tag(
    *,
    manifests_root: Path | str | None = None,
) -> dict[str, tuple[str, ...]]:
    """Map model tag to every manifest root that contains it."""
    roots = manifest_search_paths(extra_root=Path(manifests_root) if manifests_root else None)
    locations: dict[str, list[str]] = {}
    for root in roots:
        library = root / "manifests" / "registry.ollama.ai" / "library"
        if not library.is_dir():
            continue
        for family_dir in library.iterdir():
            if not family_dir.is_dir():
                continue
            for tag_path in family_dir.iterdir():
                if tag_path.is_file():
                    tag = f"{family_dir.name}:{tag_path.name}"
                    locations.setdefault(tag, []).append(str(root))
    return {tag: tuple(paths) for tag, paths in sorted(locations.items())}


def audit_model_folders(
    *,
    manifests_root: Path | str | None = None,
) -> dict[str, object]:
    """Report duplicate tags across Ollama model directories."""
    locations = model_locations_by_tag(manifests_root=manifests_root)
    duplicates = {tag: list(paths) for tag, paths in locations.items() if len(paths) > 1}
    primary = default_models_dir()
    if primary is None:
        home = Path.home() / ".ollama" / "models"
        primary = home if home.is_dir() else None
    return {
        "primary_root": str(primary) if primary else None,
        "scan_roots": list(manifest_search_paths()),
        "tag_count": len(locations),
        "locations": {tag: list(paths) for tag, paths in locations.items()},
        "duplicates": duplicates,
        "duplicate_tags": sorted(duplicates),
    }


def remove_duplicate_manifests(
    *,
    keep_root: str | Path,
    drop_roots: list[str | Path] | None = None,
) -> list[str]:
    """Delete manifest files from secondary folders when keep_root already has the tag."""
    keep = Path(keep_root).expanduser().resolve()
    drops = [Path(path).expanduser().resolve() for path in (drop_roots or manifest_search_paths())]
    drops = [path for path in drops if path != keep and path.is_dir()]

    keep_library = keep / "manifests" / "registry.ollama.ai" / "library"
    if not keep_library.is_dir():
        return []

    keep_tags: set[str] = set()
    for family_dir in keep_library.iterdir():
        if not family_dir.is_dir():
            continue
        for tag_path in family_dir.iterdir():
            if tag_path.is_file():
                keep_tags.add(f"{family_dir.name}:{tag_path.name}")

    removed: list[str] = []
    for drop in drops:
        library = drop / "manifests" / "registry.ollama.ai" / "library"
        if not library.is_dir():
            continue
        for family_dir in library.iterdir():
            if not family_dir.is_dir():
                continue
            for tag_path in list(family_dir.iterdir()):
                if not tag_path.is_file():
                    continue
                tag = f"{family_dir.name}:{tag_path.name}"
                if tag in keep_tags:
                    tag_path.unlink()
                    removed.append(f"{tag} @ {drop}")
    return removed
