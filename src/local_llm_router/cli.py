from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from local_llm_router.advice import stack_recommendation
from local_llm_router.benchmark import format_markdown_table, routed_model_mix, run_benchmark
from local_llm_router.compare import CompareRunError, format_compare_text, run_compare
from local_llm_router.discovery import discover_models
from local_llm_router.local_models import assign_tiers_from_local, list_local_models
from local_llm_router.model_registry import (
    config_search_paths,
    list_deployment_profiles,
    load_registry,
)
from local_llm_router.ollama_generate import ask_prompt_json, route_prompt_json
from local_llm_router.requirements import UsageProfile, list_usage_profiles, usage_requirements
from local_llm_router.presets import assign_recommended_tiers, list_recommended_stacks, recommended_models
from local_llm_router.setup_wizard import format_setup_summary, plan_setup, run_setup
from local_llm_router.stack_health import check_stack_health, format_stack_health
from local_llm_router.tiering import assign_tiers, describe_tiers


def _print_requirements(profile: UsageProfile, *, check: bool) -> None:
    report = usage_requirements(profile, check=check)
    status = "ready" if report.ready else "missing required items"
    print(f"{report.title} ({report.profile.value}) - {status}")
    print(report.summary)
    print("")
    for item in report.prerequisites:
        required_label = "required" if item.required else "optional"
        if item.satisfied is True:
            state = "ok"
        elif item.satisfied is False:
            state = "missing"
        else:
            state = "not checked"
        print(f"  [{state}] {item.description} ({required_label})")
        if item.install_command:
            print(f"         install: {item.install_command}")
        if item.verify_hint:
            print(f"         verify:  {item.verify_hint}")
    print("")


def _cmd_requirements(profile_name: str | None, check: bool) -> int:
    if profile_name:
        try:
            profile = UsageProfile(profile_name)
        except ValueError:
            valid = ", ".join(item.value for item in list_usage_profiles())
            print(f"Unknown profile '{profile_name}'. Valid profiles: {valid}")
            return 1
        _print_requirements(profile, check=check)
        return 0

    for profile in list_usage_profiles():
        _print_requirements(profile, check=check)
    return 0


def _add_quant_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--quant",
        choices=["default", "qat", "qat_mobile", "bf16"],
        help=(
            "Assume Gemma 4 pull quantization for VRAM sizing "
            "(qat=Unsloth UD-Q4_K_XL runtime GB; not per-prompt routing)"
        ),
    )


def _add_profile_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        help=(
            "Deployment profile override: workstation_8gb, workstation_12gb, "
            "workstation_16gb, workstation_24gb, workstation_32gb, datacenter "
            "(aliases: 8gb, 12gb, 16gb, 24gb, 32gb)"
        ),
    )


def _add_hint_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--hint",
        choices=["lookup", "explain", "design", "code", "reason"],
        help="Agent step hint: lookup, explain, design, code, reason",
    )


def _cmd_stacks(args: argparse.Namespace) -> int:
    if args.profile:
        try:
            models = recommended_models(args.profile, quant=args.quant)
            tiers = assign_tiers(models)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1
        if args.json:
            payload = {
                "profile": args.profile,
                "quant": args.quant or "default",
                "models": models,
                "tiers": describe_tiers(tiers),
            }
            return _emit_json(payload)
        print(f"Recommended stack for {args.profile}:")
        if args.quant:
            print(f"  quant: {args.quant}")
        print("  models:", ",".join(models))
        print("  tiers:")
        for key, value in describe_tiers(tiers).items():
            print(f"    {key}: {value or '-'}")
        return 0

    if args.json:
        payload = {
            "stacks": [
                {
                    "profile": item.profile,
                    "models": list(item.models),
                    "description": item.description,
                }
                for item in list_recommended_stacks()
            ]
        }
        return _emit_json(payload)
    print("Recommended specialist stacks (workstation 8–32 GB):")
    for item in list_recommended_stacks():
        print(f"  {item.profile}")
        print(f"    {item.description}")
        print(f"    models: {','.join(item.models)}")
    return 0


def _cmd_profiles(args: argparse.Namespace) -> int:
    if args.json:
        payload = {
            "profiles": [
                {
                    "name": item.name,
                    "assumed_vram_gb": item.assumed_vram_gb,
                    "apply_vram_filter": item.apply_vram_filter,
                    "description": item.description,
                }
                for item in list_deployment_profiles()
            ]
        }
        return _emit_json(payload)
    print("Deployment profiles:")
    for item in list_deployment_profiles():
        vram = item.assumed_vram_gb if item.assumed_vram_gb is not None else "n/a"
        filter_label = "on" if item.apply_vram_filter else "off"
        print(f"  {item.name}\tassumed_vram_gb={vram}\tvram_filter={filter_label}")
        print(f"    {item.description}")
    return 0


def _cmd_doctor_check_stack(args: argparse.Namespace) -> int:
    models = None
    if args.models:
        models = [part.strip() for part in args.models.split(",") if part.strip()]
    report = check_stack_health(
        profile=args.profile,
        vram_gb=args.vram_gb,
        quant=args.quant,
        base_url=args.base_url,
        models=models,
    )
    if args.json:
        payload = {
            "ready": report.ready,
            "profile": report.profile,
            "vram_gb": report.vram_gb,
            "quant": report.quant,
            "recommended": list(report.recommended),
            "resolved": list(report.resolved),
            "missing": list(report.missing),
            "pool_size": report.pool_size,
            "inventory_note": report.inventory_note,
            "findings": [
                {
                    "level": item.level,
                    "code": item.code,
                    "message": item.message,
                    "models": list(item.models),
                }
                for item in report.findings
            ],
        }
        return _emit_json(payload)
    print(format_stack_health(report))
    return 0 if report.ready else 1


def _cmd_doctor(args: argparse.Namespace) -> int:
    if args.check_stack:
        return _cmd_doctor_check_stack(args)

    advice = stack_recommendation(cursor_override_enabled=False)
    print(f"Cursor model: {advice.cursor_model}")
    print(f"Prose path: {advice.prose_path}")
    print(f"Local path: {advice.local_path}")

    try:
        tiers, models, warning = assign_tiers_from_local(
            only_vram_ok=True,
            profile=args.profile,
            config_path=args.config,
            quant_mode=args.quant,
        )
        registry = load_registry(args.config, profile=args.profile)
        vram_label = registry.assumed_vram_gb if registry.assumed_vram_gb is not None else "n/a"
        quant_label = args.quant or "default"
        print(f"\nLocal model table (profile={registry.profile}, assumed_vram_gb={vram_label}, quant={quant_label}):")
        print("  model\tweight\tvram_gb\tfamily\tvram_ok\tsource")
        for item in models:
            vram = item.vram_gb if item.vram_gb is not None else "-"
            family = item.family or "-"
            print(
                f"  {item.name}\t{item.weight}\t{vram}\t{family}\t{item.vram_ok}\t{item.source}"
            )
        print("\nDetected model tiers:")
        print(f"  SIMPLE:    {tiers.simple}")
        print(f"  MEDIUM:    {tiers.medium}")
        print(f"  COMPLEX:   {tiers.complex}")
        print(f"  REASONING: {tiers.reasoning}")
        if tiers.code:
            print(f"  CODE:      {tiers.code}")
        if warning:
            print(f"\nWarning: {warning}")
        config_paths = [str(path) for path in config_search_paths() if path.is_file()]
        if config_paths:
            print(f"\nUsing config: {config_paths[0]}")
        else:
            print("\nUsing built-in model table. Copy config/models.example.json to local-llm-router.models.json")
    except Exception as exc:
        print(f"\nOllama discovery skipped: {exc}")
    return 0


def _cmd_models(args: argparse.Namespace) -> int:
    try:
        models, warning = list_local_models(
            base_url=args.base_url,
            config_path=args.config,
            profile=args.profile,
            only_vram_ok=not args.all,
            include_disk=args.include_disk,
            quant_mode=args.quant,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    registry = load_registry(args.config, profile=args.profile)
    vram_label = registry.assumed_vram_gb if registry.assumed_vram_gb is not None else None
    if args.json:
        payload = {
            "profile": registry.profile,
            "assumed_vram_gb": vram_label,
            "quant": args.quant or "default",
            "apply_vram_filter": registry.apply_vram_filter,
            "models": [
                {
                    "name": item.name,
                    "weight": item.weight,
                    "vram_gb": item.vram_gb,
                    "family": item.family,
                    "vram_ok": item.vram_ok,
                    "source": item.source,
                    "quant_mode": item.quant_mode,
                }
                for item in models
            ],
            "warning": warning,
        }
        return _emit_json(payload)
    vram_text = registry.assumed_vram_gb if registry.assumed_vram_gb is not None else "n/a"
    print(
        f"profile={registry.profile} assumed_vram_gb={vram_text} "
        f"vram_filter={'on' if registry.apply_vram_filter else 'off'}"
    )
    print("model\tweight\tvram_gb\tfamily\tvram_ok\tsource")
    for item in models:
        vram = item.vram_gb if item.vram_gb is not None else "-"
        family = item.family or "-"
        print(f"{item.name}\t{item.weight}\t{vram}\t{family}\t{item.vram_ok}\t{item.source}")
    if warning:
        print(f"\nWarning: {warning}")
    searched = config_search_paths(args.config)
    active = next((path for path in searched if path.is_file()), None)
    if active:
        print(f"\nConfig: {active}")
    else:
        print("\nConfig: built-in table (copy config/models.example.json → local-llm-router.models.json)")
    return 0


def _cmd_tips(args: argparse.Namespace) -> int:
    from local_llm_router.startup_tips import model_recommendation_report

    lines = model_recommendation_report(
        profile=args.profile,
        include_api=args.api,
        base_url=args.base_url,
    )
    if args.json:
        return _emit_json({"ready": True, "lines": lines, "profile": args.profile})
    for line in lines:
        print(line)
    return 0


def _parse_model_names(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    names = [item.strip() for item in raw.split(",") if item.strip()]
    return names or None


def _emit_json(payload: dict) -> int:
    print(json.dumps(payload))
    return 0 if payload.get("ready", True) else 1


def _cmd_setup(args: argparse.Namespace) -> int:
    config_path = Path(args.config) if args.config else None
    result = run_setup(
        args.profile,
        base_url=args.base_url,
        config_path=config_path,
        assume_yes=args.yes,
        dry_run=args.dry_run,
        interactive=not args.yes and not args.dry_run and not args.json,
    )
    if args.json:
        payload = {
            "ready": result.ready,
            "profile": result.profile,
            "config_path": str(result.config_path),
            "pulled": list(result.pulled),
            "already_present": list(result.already_present),
            "skipped": list(result.skipped),
            "tiers": result.tiers,
            "cancelled": result.cancelled,
            "dry_run": result.dry_run,
            "error": result.error,
        }
        return _emit_json(payload)
    print(format_setup_summary(result))
    if result.cancelled:
        print("\nNo changes made. Re-run with --yes to skip confirmation.")
        return 1
    if not result.ready:
        return 1
    print("\nNext: stack doctor  |  stack ask --prompt \"what is caching?\" --hint lookup")
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    from local_llm_router.routing import explain_route
    from local_llm_router.session import configure, describe_session
    from local_llm_router.tiering import assign_tiers
    from local_llm_router.validation import validate_tier_map

    models = _parse_model_names(args.models)
    if models:
        tiers = assign_tiers(models)
        session_info: dict[str, object] = {"source": "explicit_models", "models": models}
        warnings = validate_tier_map(tiers, models, profile=args.profile)
    else:
        try:
            session = configure(profile=args.profile, quant=args.quant)
        except ValueError as exc:
            if args.json:
                return _emit_json({"ready": False, "error": str(exc)})
            print(f"Error: {exc}")
            return 1
        tiers = session.tiers
        session_info = describe_session()
        warnings = list(session.warnings)

    decision = explain_route(args.prompt, tiers, hint=args.hint)
    payload = {
        "ready": True,
        "decision": decision.to_dict(),
        "session": session_info,
        "warnings": warnings,
    }
    if args.json:
        return _emit_json(payload)
    print(f"model={decision.model} tier={decision.tier.value}")
    for line in decision.reasons:
        print(f"  - {line}")
    if warnings:
        print("Warnings:")
        for line in warnings:
            print(f"  ! {line}")
    return 0


def _cmd_route(args: argparse.Namespace) -> int:
    if getattr(args, "explain", False):
        return _cmd_explain(args)

    result = route_prompt_json(
        args.prompt,
        base_url=args.base_url,
        model_names=_parse_model_names(args.models),
        hint=args.hint,
    )
    payload = asdict(result)
    if args.json:
        return _emit_json(payload)
    if not result.ready:
        print(f"Error: {result.error}")
        return 1
    print(f"Routed to {result.model} ({result.tier})")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    result = ask_prompt_json(
        args.prompt,
        base_url=args.base_url,
        model_names=_parse_model_names(args.models),
        timeout_seconds=args.timeout,
        hint=args.hint,
    )
    payload = asdict(result)
    if args.json:
        return _emit_json(payload)
    if not result.ready:
        print(f"Error: {result.error}")
        return 1
    print(f"Routed to {result.model} ({result.tier})")
    print(result.text)
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        report = run_compare(
            model_names=_parse_model_names(args.models),
            base_url=args.base_url,
            dry_run=not args.live,
            timeout_seconds=args.timeout,
        )
    except CompareRunError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        payload = {
            "models": list(report.models),
            "rows": [
                {
                    "step": row.step,
                    "routed_tier": row.routed_tier,
                    "routed_model": row.routed_model,
                    "baseline_model": row.baseline_model,
                    "routed_latency_ms": row.routed_latency_ms,
                    "baseline_latency_ms": row.baseline_latency_ms,
                }
                for row in report.rows
            ],
            "summary": {
                "baseline_model": report.summary.baseline_model,
                "routed_models_used": report.summary.routed_models_used,
                "baseline_models_used": report.summary.baseline_models_used,
                "steps_avoided_largest": report.summary.steps_avoided_largest,
                "total_steps": report.summary.total_steps,
                "routed_total_latency_ms": report.summary.routed_total_latency_ms,
                "baseline_total_latency_ms": report.summary.baseline_total_latency_ms,
            },
        }
        return _emit_json(payload)
    print(format_compare_text(report))
    if not args.live:
        print("\nDry run only (routing). Re-run with --live to measure Ollama latency per step.")
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    report = run_benchmark(model_names=_parse_model_names(args.models))
    if args.markdown:
        print(format_markdown_table(report))
        print("")
        print("tier_counts:", report.tier_counts)
        print("model_mix:", routed_model_mix(report))
        print("always_biggest_would_use:", report.models[-1] if report.models else "")
        return 0
    if args.json:
        payload = {
            "models": list(report.models),
            "tier_counts": report.tier_counts,
            "model_mix": routed_model_mix(report),
            "rows": [
                {
                    "id": row.id,
                    "tier": row.tier,
                    "model": row.model,
                    "note": row.note,
                    "prompt": row.prompt,
                }
                for row in report.rows
            ],
        }
        return _emit_json(payload)
    for row in report.rows:
        print(f"{row.id}\t{row.tier}\t{row.model}\t{row.note}")
    return 0


def _add_ollama_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", required=True, help="Prompt text to route or ask")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL for model discovery and generation",
    )
    parser.add_argument(
        "--models",
        help="Comma-separated model names (skip Ollama discovery when set)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="llm-router", description="local-llm-router helper CLI")
    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser("doctor", help="Show stack advice and optional Ollama tiers")
    _add_profile_arg(doctor_parser)
    doctor_parser.add_argument(
        "--config",
        help="Path to local-llm-router.models.json (or set LOCAL_LLM_ROUTER_MODELS_CONFIG)",
    )
    _add_quant_arg(doctor_parser)
    doctor_parser.add_argument(
        "--check-stack",
        action="store_true",
        help="Offline stack health: missing models, duplicates, routing spread (exit 1 if not ready)",
    )
    doctor_parser.add_argument(
        "--vram-gb",
        type=int,
        choices=[8, 12, 16, 24, 32],
        help="GPU VRAM for recommended stack (alternative to --profile)",
    )
    doctor_parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL for inventory scan",
    )
    doctor_parser.add_argument(
        "--models",
        help="Comma-separated stack override when using --check-stack",
    )
    doctor_parser.add_argument("--json", action="store_true", help="JSON output (with --check-stack)")
    doctor_parser.set_defaults(handler=_cmd_doctor)

    requirements_parser = subparsers.add_parser(
        "requirements",
        help="Show prerequisites for each usage profile",
    )
    requirements_parser.add_argument(
        "profile",
        nargs="?",
        help="Profile id: core, ollama_discovery, local_assistant, cli_doctor",
    )
    requirements_parser.add_argument(
        "--check",
        action="store_true",
        help="Probe this machine (Python, requests, Ollama)",
    )
    requirements_parser.set_defaults(handler=lambda args: _cmd_requirements(args.profile, args.check))

    route_parser = subparsers.add_parser("route", help="Route a prompt to a model tier")
    _add_ollama_args(route_parser)
    _add_hint_arg(route_parser)
    _add_profile_arg(route_parser)
    _add_quant_arg(route_parser)
    route_parser.add_argument(
        "--explain",
        action="store_true",
        help="Print routing decision trace (uses configure/profile when --models omitted)",
    )
    route_parser.set_defaults(handler=_cmd_route)

    explain_parser = subparsers.add_parser(
        "explain",
        help="Show why a prompt maps to a tier and model (JSON-friendly)",
    )
    explain_parser.add_argument("--prompt", required=True, help="Prompt text to route")
    explain_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    _add_hint_arg(explain_parser)
    _add_profile_arg(explain_parser)
    _add_quant_arg(explain_parser)
    explain_parser.add_argument(
        "--models",
        help="Comma-separated model list (power user — bypasses preset discovery)",
    )
    explain_parser.set_defaults(handler=_cmd_explain)

    ask_parser = subparsers.add_parser("ask", help="Route a prompt and generate via Ollama")
    _add_ollama_args(ask_parser)
    _add_hint_arg(ask_parser)
    ask_parser.add_argument("--timeout", type=int, default=60, help="Ollama request timeout in seconds")
    ask_parser.set_defaults(handler=_cmd_ask)

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare local-llm-router routing vs always-largest on 5-step agent loop",
    )
    compare_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    compare_parser.add_argument(
        "--live",
        action="store_true",
        help="Call Ollama per step for routed and baseline latency (slow)",
    )
    compare_parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL (used with --live)",
    )
    compare_parser.add_argument("--timeout", type=int, default=90, help="Ollama timeout in seconds")
    compare_parser.add_argument(
        "--models",
        default="gemma4:e4b,qwen3:8b,qwen3:14b",
        help="Comma-separated model stack (default: Gemma simple + Qwen mid/complex)",
    )
    compare_parser.set_defaults(handler=_cmd_compare)

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run fixed 10-prompt routing benchmark (no inference)",
    )
    benchmark_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    benchmark_parser.add_argument("--markdown", action="store_true", help="Print markdown table")
    benchmark_parser.add_argument(
        "--models",
        help="Comma-separated model names (default qwen3:4b,qwen3:8b,qwen3:14b,qwen3:30b-a3b)",
    )
    benchmark_parser.set_defaults(handler=_cmd_benchmark)

    models_parser = subparsers.add_parser(
        "models",
        help="List local Ollama models with registry weights and VRAM hints",
    )
    models_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    models_parser.add_argument(
        "--config",
        help="Path to local-llm-router.models.json (or set LOCAL_LLM_ROUTER_MODELS_CONFIG)",
    )
    models_parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL",
    )
    models_parser.add_argument(
        "--include-disk",
        action="store_true",
        help="Also scan Ollama manifest folders on disk (OLLAMA_MODELS, ~/.ollama/models, ~/dev/Tools/.ollama/models)",
    )
    models_parser.add_argument(
        "--all",
        action="store_true",
        help="Include models above assumed_vram_gb (ignored when profile=datacenter)",
    )
    _add_profile_arg(models_parser)
    _add_quant_arg(models_parser)
    models_parser.set_defaults(handler=_cmd_models)

    tips_parser = subparsers.add_parser(
        "tips",
        help="Show installed vs recommended local models (community picks)",
    )
    tips_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    tips_parser.add_argument(
        "--api",
        action="store_true",
        help="Include models from running Ollama /api/tags",
    )
    tips_parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL when --api is set",
    )
    _add_profile_arg(tips_parser)
    tips_parser.set_defaults(handler=_cmd_tips)

    profiles_parser = subparsers.add_parser(
        "profiles",
        help="List workstation VRAM presets and the datacenter profile",
    )
    profiles_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    profiles_parser.set_defaults(handler=_cmd_profiles)

    stacks_parser = subparsers.add_parser(
        "stacks",
        help="List recommended specialist model stacks for workstation profiles",
    )
    stacks_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    _add_profile_arg(stacks_parser)
    _add_quant_arg(stacks_parser)
    stacks_parser.set_defaults(handler=_cmd_stacks)

    setup_parser = subparsers.add_parser(
        "setup",
        help="Pick a VRAM preset, consent to Ollama pulls, write local-llm-router.models.json",
    )
    setup_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    _add_profile_arg(setup_parser)
    setup_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts (non-interactive installs)",
    )
    setup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned pulls and tier map without downloading",
    )
    setup_parser.add_argument(
        "--config",
        help="Write config to this path (default ./local-llm-router.models.json)",
    )
    setup_parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL",
    )
    setup_parser.set_defaults(handler=_cmd_setup)

    args = parser.parse_args(argv)
    if not args.command:
        return _cmd_doctor(argparse.Namespace(profile=None, config=None, quant=None))
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
