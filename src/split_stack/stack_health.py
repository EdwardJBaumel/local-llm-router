"""Offline stack health checks — missing models, duplicates, routing spread, quant honesty."""

from __future__ import annotations

from dataclasses import dataclass

from split_stack.discovery import audit_model_folders, list_model_inventory
from split_stack.poc_models import resolve_stack_against_pool, stack_payload
from split_stack.presets import recommended_models
from split_stack.quantization import adjust_vram_for_quant, normalize_quant_mode, pull_guidance_lines
from split_stack.session import default_profile_from_env, profile_for_vram_gb


@dataclass(frozen=True)
class ModelTagInfo:
    name: str
    size_bytes: int
    quantization_level: str | None


@dataclass(frozen=True)
class StackHealthFinding:
    level: str  # ok, warn, error
    code: str
    message: str
    models: tuple[str, ...] = ()


@dataclass(frozen=True)
class StackHealthReport:
    ready: bool
    profile: str
    vram_gb: int | None
    quant: str
    recommended: tuple[str, ...]
    resolved: tuple[str, ...]
    missing: tuple[str, ...]
    pool_size: int
    findings: tuple[StackHealthFinding, ...]
    inventory_note: str | None = None


def check_stack_health(
    *,
    profile: str | None = None,
    vram_gb: int | None = None,
    quant: str | None = None,
    base_url: str = "http://127.0.0.1:11434",
    models: list[str] | None = None,
    source: str = "both",
) -> StackHealthReport:
    """Check recommended stack against local inventory (offline; no upstream registry)."""
    quant_mode = normalize_quant_mode(quant)
    if vram_gb is not None:
        resolved_profile = profile_for_vram_gb(vram_gb)
    else:
        resolved_profile = profile or default_profile_from_env()
        vram_gb = _vram_for_profile(resolved_profile)

    if models:
        recommended = tuple(models)
        payload = stack_payload(
            vram_gb=vram_gb or 12,
            quant=quant_mode,
            base_url=base_url,
            source=source,
            models_override=list(models),
        )
        resolved = tuple(payload.get("resolved_models") or ())
        missing = tuple(payload.get("missing_models") or ())
        inventory_note = payload.get("inventory_note")
        if isinstance(inventory_note, str):
            pass
        else:
            inventory_note = None
        pool_size = int(payload.get("pool_size") or 0)
    else:
        recommended = tuple(recommended_models(resolved_profile, quant=quant_mode))
        inventory = list_model_inventory(base_url=base_url)
        if source == "api":
            pool = list(inventory.api_models)
        elif source == "disk":
            pool = list(inventory.disk_models)
        else:
            pool = sorted(set(inventory.api_models) | set(inventory.disk_models))
        resolved_list, missing_list, _warning = resolve_stack_against_pool(
            list(recommended),
            pool,
        )
        resolved = tuple(resolved_list)
        missing = tuple(missing_list)
        inventory_note = inventory.note
        pool_size = len(pool)

    findings: list[StackHealthFinding] = []

    for name in recommended:
        if name in missing:
            findings.append(
                StackHealthFinding(
                    level="error",
                    code="missing",
                    message=f"{name} is recommended but not found in local inventory.",
                    models=(name,),
                )
            )
        elif name in resolved:
            findings.append(
                StackHealthFinding(
                    level="ok",
                    code="present",
                    message=f"{name} is installed.",
                    models=(name,),
                )
            )

    if len(resolved) < 2:
        findings.append(
            StackHealthFinding(
                level="error",
                code="routing_spread",
                message=(
                    f"Only {len(resolved)} model(s) available for routing "
                    f"({', '.join(resolved) or 'none'}). Need at least 2 for tier spread."
                ),
                models=resolved,
            )
        )
    elif missing:
        findings.append(
            StackHealthFinding(
                level="warn",
                code="partial_stack",
                message=(
                    f"Using {len(resolved)} installed model(s); "
                    f"{len(missing)} recommended tag(s) missing."
                ),
                models=resolved,
            )
        )
    else:
        findings.append(
            StackHealthFinding(
                level="ok",
                code="stack_complete",
                message=f"All {len(recommended)} recommended model(s) are installed.",
                models=resolved,
            )
        )

    audit = audit_model_folders()
    duplicate_tags = audit.get("duplicate_tags") or []
    if duplicate_tags:
        dup_list = tuple(str(tag) for tag in duplicate_tags)
        findings.append(
            StackHealthFinding(
                level="warn",
                code="duplicate_tags",
                message=(
                    f"Duplicate tags across Ollama folders: {', '.join(dup_list)}. "
                    "Keep one models directory or run audit cleanup."
                ),
                models=dup_list,
            )
        )

    findings.extend(
        _quant_mismatch_findings(
            quant_mode=quant_mode,
            model_names=tuple(name for name in resolved if name not in missing),
            base_url=base_url,
        )
    )

    ready = len(resolved) >= 2
    return StackHealthReport(
        ready=ready,
        profile=resolved_profile,
        vram_gb=vram_gb,
        quant=quant_mode,
        recommended=recommended,
        resolved=resolved,
        missing=missing,
        pool_size=pool_size,
        findings=tuple(findings),
        inventory_note=inventory_note,
    )


def format_stack_health(report: StackHealthReport) -> str:
    lines: list[str] = []
    vram_label = f"{report.vram_gb} GB" if report.vram_gb is not None else report.profile
    lines.append(f"Stack health ({vram_label}, quant={report.quant})")
    lines.append(f"  Recommended: {', '.join(report.recommended) or '-'}")
    lines.append(f"  Resolved:    {', '.join(report.resolved) or '-'}")
    if report.missing:
        lines.append(f"  Missing:     {', '.join(report.missing)}")
    lines.append(f"  Inventory:   {report.pool_size} tag(s) seen (API + disk)")
    if report.inventory_note:
        lines.append(f"  Note:        {report.inventory_note}")
    lines.append("")
    for item in report.findings:
        prefix = {"ok": "OK", "warn": "WARN", "error": "ERROR"}.get(item.level, item.level.upper())
        lines.append(f"  [{prefix}] {item.message}")
    lines.append("")
    if report.ready:
        lines.append("Routing: ready (2+ models)")
    else:
        lines.append("Routing: not ready — install more models or adjust profile/VRAM.")
    return "\n".join(lines)


def _vram_for_profile(profile: str) -> int | None:
    from split_stack.model_registry import DEPLOYMENT_PROFILES

    spec = DEPLOYMENT_PROFILES.get(profile)
    if spec is None:
        return None
    return spec.assumed_vram_gb


def _fetch_ollama_tag_info(
    *,
    base_url: str = "http://127.0.0.1:11434",
) -> dict[str, ModelTagInfo]:
    try:
        import requests
    except ImportError:
        return {}

    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except Exception:
        return {}

    out: dict[str, ModelTagInfo] = {}
    payload = response.json() or {}
    for item in payload.get("models") or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        details = item.get("details") or {}
        quant = details.get("quantization_level")
        out[name] = ModelTagInfo(
            name=name,
            size_bytes=int(item.get("size") or 0),
            quantization_level=str(quant) if quant else None,
        )
    return out


def _is_gemma_tag(name: str) -> bool:
    family = name.split(":")[0].lower()
    return family.startswith("gemma")


def _tag_suggests_qat(name: str) -> bool:
    lowered = name.lower()
    markers = ("qat", "ud-q4", "ud_q4", "unsloth", "gemma-4-qat")
    return any(marker in lowered for marker in markers)


def _tag_suggests_bf16(name: str) -> bool:
    lowered = name.lower()
    return "bf16" in lowered or "-it-bf16" in lowered


def _quant_mismatch_findings(
    *,
    quant_mode: str,
    model_names: tuple[str, ...],
    base_url: str,
) -> list[StackHealthFinding]:
    if quant_mode == "default":
        return []

    tag_info = _fetch_ollama_tag_info(base_url=base_url)
    if not tag_info:
        return [
            StackHealthFinding(
                level="warn",
                code="quant_check_skipped",
                message=(
                    "Quant check skipped — Ollama /api/tags unreachable or "
                    "install split-stack[ollama] for requests."
                ),
            )
        ]

    findings: list[StackHealthFinding] = []
    gemma_tags = [name for name in model_names if _is_gemma_tag(name)]
    if not gemma_tags:
        return findings

    for name in gemma_tags:
        info = tag_info.get(name)
        if info is None:
            continue

        expected_gb = adjust_vram_for_quant(name, base_vram_gb=999, quant_mode=quant_mode)
        size_gb = info.size_bytes / (1024**3) if info.size_bytes else 0.0
        quant_label = info.quantization_level or "unknown"

        if quant_mode == "bf16":
            if not _tag_suggests_bf16(name) and quant_label not in {"F16", "BF16", "FP16"}:
                findings.append(
                    StackHealthFinding(
                        level="warn",
                        code="quant_mismatch",
                        message=(
                            f"{name}: quant=bf16 but installed as {quant_label} "
                            f"({size_gb:.1f} GB on disk). VRAM sizing may be wrong."
                        ),
                        models=(name,),
                    )
                )
            continue

        # qat / qat_mobile — expect smaller runtime than library Q4_K_M pulls
        if _tag_suggests_qat(name):
            findings.append(
                StackHealthFinding(
                    level="ok",
                    code="quant_ok",
                    message=f"{name}: tag looks QAT-aligned ({quant_label}, {size_gb:.1f} GB).",
                    models=(name,),
                )
            )
            continue

        oversized = expected_gb is not None and size_gb > expected_gb * 1.35
        library_ptq = quant_label in {"Q4_K_M", "Q4_0", "Q5_K_M", "Q5_0"}
        if oversized or library_ptq:
            expected_text = f"~{expected_gb} GB runtime" if expected_gb else "smaller QAT runtime"
            findings.append(
                StackHealthFinding(
                    level="warn",
                    code="quant_mismatch",
                    message=(
                        f"{name}: quant={quant_mode} expects {expected_text} but installed "
                        f"{quant_label} at {size_gb:.1f} GB — likely library PTQ, not QAT."
                    ),
                    models=(name,),
                )
            )

    if any(item.code == "quant_mismatch" for item in findings):
        hint = pull_guidance_lines(quant_mode)
        if hint:
            findings.append(
                StackHealthFinding(
                    level="warn",
                    code="quant_hint",
                    message=hint[0],
                )
            )

    return findings
