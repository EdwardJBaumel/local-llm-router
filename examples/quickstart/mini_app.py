"""Hands-on quickstart: profile, tiers, routing, optional Ollama generation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
DEFAULT_CONFIG = EXAMPLE_DIR / "local-llm-router.models.json"

DEFAULT_MODELS = ["qwen3:4b", "qwen3:8b", "qwen3:14b", "qwen3:30b-a3b"]

SAMPLE_PROMPTS: tuple[tuple[str, str], ...] = (
    ("simple", "what is caching?"),
    ("medium", "compare JWT vs session cookies for a small API"),
    ("complex", "design a distributed webhook retry strategy"),
    ("reasoning", "prove this token expiry policy step by step"),
)


def _ensure_config() -> Path:
    config = Path(os.environ.get("LOCAL_LLM_ROUTER_MODELS_CONFIG", DEFAULT_CONFIG))
    if not config.is_file():
        raise SystemExit(
            f"Config not found: {config}\n"
            f"Copy {DEFAULT_CONFIG.name} or set LOCAL_LLM_ROUTER_MODELS_CONFIG."
        )
    os.environ.setdefault("LOCAL_LLM_ROUTER_MODELS_CONFIG", str(config))
    return config


def _section(title: str) -> None:
    print("")
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_profile(*, profile: str | None) -> None:
    from local_llm_router.model_registry import load_registry

    registry = load_registry(profile=profile)
    vram = registry.assumed_vram_gb if registry.assumed_vram_gb is not None else "n/a"
    print(f"profile={registry.profile}  assumed_vram_gb={vram}  vram_filter={registry.apply_vram_filter}")


def _print_tiers(model_names: list[str]) -> None:
    from local_llm_router import assign_tiers

    tiers = assign_tiers(model_names)
    print("Tier map (from your model list):")
    print(f"  SIMPLE:    {tiers.simple}")
    print(f"  MEDIUM:    {tiers.medium}")
    print(f"  COMPLEX:   {tiers.complex}")
    print(f"  REASONING: {tiers.reasoning}")


def _print_routes(model_names: list[str]) -> None:
    from local_llm_router import assign_tiers, route_prompt

    tiers = assign_tiers(model_names)
    print("Prompt routing (no inference):")
    print("label\t\ttier\t\tmodel")
    for label, prompt in SAMPLE_PROMPTS:
        tier, model = route_prompt(prompt, tiers)
        print(f"{label:<12}\t{tier.value:<12}\t{model}")


def _print_local_models(*, profile: str | None, base_url: str) -> None:
    from local_llm_router.local_models import list_local_models

    models, warning = list_local_models(
        base_url=base_url,
        profile=profile,
        only_vram_ok=True,
    )
    print(f"Ollama models passing VRAM filter ({len(models)}):")
    for item in models[:12]:
        print(f"  {item.name}\tweight={item.weight}\tvram_gb={item.vram_gb}\tvram_ok={item.vram_ok}")
    if len(models) > 12:
        print(f"  ... and {len(models) - 12} more")
    if warning:
        print(f"Warning: {warning}")


def _live_ask(*, prompt: str, model_names: list[str], base_url: str) -> None:
    from local_llm_router.ollama_generate import ask_prompt_json

    result = ask_prompt_json(
        prompt,
        base_url=base_url,
        model_names=model_names,
    )
    print(json.dumps(
        {
            "tier": result.tier,
            "model": result.model,
            "ready": result.ready,
            "error": result.error,
            "text_preview": result.text[:240].replace("\n", " ") if result.text else "",
        },
        indent=2,
    ))


def run_tour(
    *,
    profile: str | None,
    model_names: list[str],
    base_url: str,
    live: bool,
) -> int:
    config = _ensure_config()
    _section("1. Config")
    print(f"Using: {config}")
    print("Tip: edit deployment_profile in that file (e.g. workstation_32gb for a 5090).")
    _print_profile(profile=profile)

    _section("2. Build tier map")
    _print_tiers(model_names)

    _section("3. Route sample prompts")
    _print_routes(model_names)

    _section("4. Benchmark (library, no Ollama)")
    from local_llm_router.benchmark import format_markdown_table, routed_model_mix, run_benchmark

    report = run_benchmark(model_names=model_names)
    print(format_markdown_table(report))
    print("model_mix:", routed_model_mix(report))

    _section("5. Discover local models (needs Ollama + local-llm-router[ollama])")
    try:
        _print_local_models(profile=profile, base_url=base_url)
    except Exception as exc:
        print(f"Skipped: {exc}")
        print("Install: pip install -e \".[ollama]\"  and start Ollama.")

    if live:
        _section("6. Live ask (route + generate one prompt)")
        _live_ask(
            prompt=SAMPLE_PROMPTS[0][1],
            model_names=model_names,
            base_url=base_url,
        )
    else:
        _section("6. Live ask (skipped)")
        print('Re-run with --live to call Ollama on "what is caching?"')

    _section("Next steps")
    print("  stack profiles")
    print("  stack route --prompt \"design webhook retries\" --json --models " + ",".join(model_names))
    print("  python examples/agent_runner/run.py")
    print(f"  Docs: {REPO_ROOT / 'docs' / 'DATACENTER.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="local-llm-router quickstart tour")
    parser.add_argument("--tour", action="store_true", help="Run the full guided walkthrough")
    parser.add_argument(
        "--profile",
        help="Override deployment profile (e.g. workstation_24gb, 32gb, datacenter)",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated model ladder",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--live", action="store_true", help="Call Ollama once at end of tour")
    parser.add_argument("--prompt", help="Route a single prompt and exit")
    args = parser.parse_args(argv)

    _ensure_config()
    model_names = [part.strip() for part in args.models.split(",") if part.strip()]

    if args.prompt:
        from local_llm_router import assign_tiers, route_prompt

        tiers = assign_tiers(model_names)
        tier, model = route_prompt(args.prompt, tiers)
        print(json.dumps({"prompt": args.prompt, "tier": tier.value, "model": model}))
        return 0

    if args.tour or len(sys.argv) == 1:
        return run_tour(
            profile=args.profile,
            model_names=model_names,
            base_url=args.base_url,
            live=args.live,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
