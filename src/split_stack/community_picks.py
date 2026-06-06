"""Community model picks — editable JSON, sourced from r/LocalLLaMA megathreads."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_PACKAGE_DEFAULT = Path(__file__).resolve().parents[2] / "config" / "community_picks.json"


@dataclass(frozen=True)
class CommunityPick:
    model: str
    note: str
    rank: int = 1


@dataclass(frozen=True)
class HintCommunityGuide:
    hint_id: str
    reddit_category: str
    vram_tier: str
    picks: tuple[CommunityPick, ...]


@dataclass(frozen=True)
class FocusStack:
    id: str
    label: str
    description: str
    models: tuple[str, ...]


def config_search_paths(explicit: str | None = None) -> list[Path]:
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit))
    env_path = os.environ.get("SPLIT_STACK_COMMUNITY_CONFIG", "").strip()
    if env_path:
        paths.append(Path(env_path))
    paths.extend(
        [
            Path.cwd() / "split-stack.community.json",
            Path.cwd() / "config" / "community_picks.json",
            _PACKAGE_DEFAULT,
        ]
    )
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


@lru_cache(maxsize=4)
def _load_raw(config_path: str | None = None) -> dict[str, Any]:
    for path in config_search_paths(config_path):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    raise FileNotFoundError(
        "community picks config not found. Copy config/community_picks.json "
        "or set SPLIT_STACK_COMMUNITY_CONFIG."
    )


def load_community_config(config_path: str | None = None) -> dict[str, Any]:
    return _load_raw(config_path)


def vram_tier_for_profile(profile: str, *, config_path: str | None = None) -> str:
    raw = _load_raw(config_path)
    mapping = raw.get("profile_to_vram_tier", {})
    return str(mapping.get(profile, "M"))


def picks_for_hint(
    hint_id: str,
    *,
    vram_tier: str = "M",
    config_path: str | None = None,
) -> tuple[CommunityPick, ...]:
    raw = _load_raw(config_path)
    hint_block = raw.get("hints", {}).get(hint_id, {})
    tier_picks = hint_block.get("picks", {}).get(vram_tier, [])
    if not tier_picks and vram_tier != "M":
        tier_picks = hint_block.get("picks", {}).get("M", [])
    result: list[CommunityPick] = []
    for index, item in enumerate(tier_picks, start=1):
        if isinstance(item, str):
            result.append(CommunityPick(model=item, note="", rank=index))
        else:
            result.append(
                CommunityPick(
                    model=str(item.get("model", "")),
                    note=str(item.get("note", "")),
                    rank=index,
                )
            )
    return tuple(p for p in result if p.model)


def focus_stack(
    focus_id: str,
    *,
    vram_tier: str = "M",
    config_path: str | None = None,
) -> FocusStack | None:
    raw = _load_raw(config_path)
    block = raw.get("focus_stacks", {}).get(focus_id)
    if not block:
        return None
    by_vram = block.get("by_vram", {})
    models = by_vram.get(vram_tier) or by_vram.get("M") or []
    return FocusStack(
        id=focus_id,
        label=str(block.get("label", focus_id)),
        description=str(block.get("description", "")),
        models=tuple(str(name) for name in models),
    )


def list_focus_stacks(
    *,
    vram_tier: str = "M",
    config_path: str | None = None,
) -> tuple[FocusStack, ...]:
    raw = _load_raw(config_path)
    stacks: list[FocusStack] = []
    for focus_id in raw.get("focus_stacks", {}):
        item = focus_stack(focus_id, vram_tier=vram_tier, config_path=config_path)
        if item and item.models:
            stacks.append(item)
    return tuple(stacks)


def community_index_for_model(
    model_name: str,
    *,
    vram_tier: str = "M",
    config_path: str | None = None,
) -> tuple[str, ...]:
    """Hint ids where this model appears in community picks."""
    lowered = model_name.lower()
    hints: list[str] = []
    for hint_id in ("lookup", "explain", "design", "code", "reason"):
        for pick in picks_for_hint(hint_id, vram_tier=vram_tier, config_path=config_path):
            pick_lower = pick.model.lower()
            if pick_lower == lowered or pick_lower in lowered or lowered.startswith(pick_lower):
                hints.append(hint_id)
                break
    return tuple(hints)


def recommended_models_for_tier(
    *,
    vram_tier: str = "M",
    config_path: str | None = None,
) -> dict[str, str]:
    """Flatten community picks to model -> best note for tier."""
    ranked: dict[str, str] = {}
    for hint_id in ("lookup", "explain", "design", "code", "reason"):
        for pick in picks_for_hint(hint_id, vram_tier=vram_tier, config_path=config_path):
            if pick.model not in ranked and pick.note:
                ranked[pick.model] = pick.note
            elif pick.model not in ranked:
                ranked[pick.model] = f"Community pick for {hint_id}"
    creative = _load_raw(config_path).get("not_in_agent_stack", {}).get("creative_rp", {})
    for item in creative.get("picks", {}).get(vram_tier, []):
        if isinstance(item, dict):
            model = str(item.get("model", ""))
            note = str(item.get("note", ""))
        else:
            model = str(item)
            note = "Creative / RP (separate from agent stack)"
        if model and model not in ranked:
            ranked[model] = note
    return ranked


def community_note_for_model(
    model_name: str,
    *,
    vram_tier: str = "M",
    config_path: str | None = None,
) -> str | None:
    notes = recommended_models_for_tier(vram_tier=vram_tier, config_path=config_path)
    if model_name in notes:
        return notes[model_name]
    lowered = model_name.lower()
    for key, note in notes.items():
        if key.lower() in lowered or lowered.startswith(key.lower()):
            return note
    return None


def build_community_guide(
    *,
    profile: str = "workstation_12gb",
    config_path: str | None = None,
) -> dict[str, Any]:
    """Payload for CLI/demo: hints + focus stacks for a workstation profile."""
    raw = _load_raw(config_path)
    vram_tier = vram_tier_for_profile(profile, config_path=config_path)
    hints: list[dict[str, Any]] = []
    for hint_id, block in raw.get("hints", {}).items():
        picks = picks_for_hint(hint_id, vram_tier=vram_tier, config_path=config_path)
        hints.append(
            {
                "hint_id": hint_id,
                "reddit_category": block.get("reddit_category", ""),
                "vram_tier": vram_tier,
                "picks": [{"model": p.model, "note": p.note, "rank": p.rank} for p in picks],
            }
        )
    creative = raw.get("not_in_agent_stack", {}).get("creative_rp", {})
    creative_picks = creative.get("picks", {}).get(vram_tier, [])
    return {
        "source": raw.get("source", ""),
        "vram_tier": vram_tier,
        "vram_tier_label": raw.get("vram_tiers", {}).get(vram_tier, vram_tier),
        "profile": profile,
        "hints": hints,
        "focus_stacks": [
            {
                "id": item.id,
                "label": item.label,
                "description": item.description,
                "models": list(item.models),
            }
            for item in list_focus_stacks(vram_tier=vram_tier, config_path=config_path)
        ],
        "creative_rp": [
            item if isinstance(item, dict) else {"model": item, "note": ""}
            for item in creative_picks
        ],
    }
