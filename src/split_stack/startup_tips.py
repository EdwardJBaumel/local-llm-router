"""Import-time and CLI tips: scan local models and surface community recommendations."""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("split_stack")

_emitted = False


def _import_tips_mode() -> str:
    return os.environ.get("SPLIT_STACK_IMPORT_TIPS", "off").strip().lower()


def _is_disabled(mode: str) -> bool:
    return mode in {"0", "false", "no", "off", "quiet"}


def _should_echo_stderr(mode: str) -> bool:
    if mode in {"1", "true", "yes", "stderr", "on"}:
        return True
    if mode != "auto":
        return False
    if not sys.stderr.isatty():
        return False
    if logger.handlers:
        return False
    root = logging.getLogger()
    return not root.handlers


def _default_report_profile() -> str:
    from split_stack.session import default_profile_from_env

    return default_profile_from_env()


def model_recommendation_report(
    *,
    profile: str | None = None,
    include_api: bool = False,
    base_url: str = "http://127.0.0.1:11434",
) -> list[str]:
    """Build human-readable lines about installed vs recommended models."""
    from split_stack.community_picks import (
        focus_stack,
        recommended_models_for_tier,
        vram_tier_for_profile,
    )
    from split_stack.discovery import audit_model_folders, discover_models_from_disk, list_model_inventory
    from split_stack.model_registry import normalize_deployment_profile

    profile_name = normalize_deployment_profile(profile or _default_report_profile())
    vram_tier = vram_tier_for_profile(profile)

    if include_api:
        inventory = list_model_inventory(base_url=base_url)
        installed = sorted(set(inventory.api_models) | set(inventory.disk_models))
        primary = inventory.manifest_roots[0] if inventory.manifest_roots else None
    else:
        installed = discover_models_from_disk()
        audit = audit_model_folders()
        primary = audit.get("primary_root")

    lines: list[str] = []
    if not installed:
        lines.append("split-stack: no local Ollama models found on disk.")
        lines.append(
            "  Starter agent stack: ollama pull gemma4:e4b && "
            "ollama pull qwen3:8b && ollama pull qwen3:14b"
        )
        lines.append("  Then: stack models --include-disk")
        return lines

    header = f"split-stack: {len(installed)} local model(s)"
    if primary:
        header += f" under {primary}"
    lines.append(f"{header} (profile {profile_name}, tier {vram_tier}).")

    stack = focus_stack("agentic", vram_tier=vram_tier)
    if stack and stack.models:
        have = [name for name in stack.models if name in installed]
        missing_stack = [name for name in stack.models if name not in installed]
        lines.append(f"  Reddit agent stack: {', '.join(stack.models)}")
        if have:
            lines.append(f"  Installed from stack: {', '.join(have)}")
        if missing_stack:
            lines.append(f"  Pull for routing spread: {', '.join(missing_stack)}")

    installed_lower = {name.lower() for name in installed}
    recommended = recommended_models_for_tier(vram_tier=vram_tier)
    missing_picks: list[str] = []
    for model_name in recommended:
        lowered = model_name.lower()
        if lowered in installed_lower:
            continue
        if any(lowered in name or name.startswith(lowered) for name in installed_lower):
            continue
        missing_picks.append(model_name)

    if missing_picks:
        preview = ", ".join(missing_picks[:6])
        if len(missing_picks) > 6:
            preview += ", ..."
        lines.append(f"  Community picks to explore: {preview}")

    extras = sorted(
        name
        for name in installed
        if stack and name not in stack.models and name not in recommended
    )
    if extras:
        preview = ", ".join(extras[:6])
        if len(extras) > 6:
            preview += ", ..."
        lines.append(f"  Also on disk (not in default stack): {preview}")

    audit = audit_model_folders()
    duplicate_tags = audit.get("duplicate_tags") or []
    if duplicate_tags:
        lines.append(
            "  Duplicate tags across folders: "
            f"{', '.join(duplicate_tags)} — keep one Ollama models directory."
        )

    lines.append("  Commands: stack models --include-disk  |  stack tips  |  stack stacks")
    return lines


def emit_import_tips(
    *,
    profile: str | None = None,
    include_api: bool = False,
    base_url: str = "http://127.0.0.1:11434",
) -> None:
    """Log model recommendations once per process (controlled by SPLIT_STACK_IMPORT_TIPS)."""
    global _emitted
    if _emitted:
        return

    mode = _import_tips_mode()
    if _is_disabled(mode):
        return

    _emitted = True
    try:
        lines = model_recommendation_report(
            profile=profile or _default_report_profile(),
            include_api=include_api,
            base_url=base_url,
        )
    except Exception as exc:
        logger.debug("split-stack import tips skipped: %s", exc)
        return

    for line in lines:
        logger.info(line)

    if _should_echo_stderr(mode):
        print("\n".join(lines), file=sys.stderr)


def reset_import_tips_for_tests() -> None:
    """Allow tests to re-run emit_import_tips."""
    global _emitted
    _emitted = False
