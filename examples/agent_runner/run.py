"""Simulated multi-step agent loop — session or explicit routing."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from enum import Enum

from split_stack import TierMap, configure, describe_session, explain, get_session, route
from split_stack.ollama_generate import generate_text
from split_stack.routing import explain_route
from split_stack.tiering import assign_tiers
from split_stack.session import reset_session_for_tests


class RoutingMode(str, Enum):
    SESSION_PRESET = "session-preset"
    SESSION_MODELS = "session-models"
    SESSION_CUSTOM = "session-custom"
    EXPLICIT = "explicit"


@dataclass(frozen=True)
class AgentStep:
    name: str
    prompt: str
    hint: str | None = None


DEFAULT_STEPS: tuple[AgentStep, ...] = (
    AgentStep("understand_goal", "Summarise the user goal: add auth to a Flask API", "explain"),
    AgentStep("quick_lookup", "what is JWT in one sentence?", "lookup"),
    AgentStep("compare_options", "compare session cookies vs JWT for a small SaaS API", "explain"),
    AgentStep("design", "design a webhook retry strategy with idempotency keys", "design"),
    AgentStep("reason", "prove this token expiry policy step by step", "reason"),
)

DEFAULT_MODELS = ["gemma4:e4b", "qwen3:8b", "qwen3:14b"]
DEFAULT_MODELS_WITH_CODER = [*DEFAULT_MODELS, "deepseek-coder:6.7b"]


def _safe(text: str) -> str:
    return text.replace("\u2192", "->").replace("\u2014", "-")


@dataclass
class StepResult:
    step: str
    tier: str
    model: str
    hint: str | None
    reasons: list[str]
    latency_ms: int | None
    preview: str
    skipped_inference: bool


def _custom_tier_map() -> TierMap:
    return TierMap(
        simple="gemma4:e4b",
        medium="qwen3:8b",
        complex="qwen3:14b",
        reasoning="qwen3:14b",
        code="deepseek-coder:6.7b",
    )


def setup_routing(
    mode: RoutingMode,
    *,
    profile: str | None,
    vram_gb: int | None,
    quant: str | None,
    model_names: list[str] | None,
) -> tuple[RoutingMode, object | None]:
    """Return (mode, explicit_tiers | None). Session modes leave explicit_tiers None."""
    reset_session_for_tests()

    if mode == RoutingMode.EXPLICIT:
        names = model_names or DEFAULT_MODELS
        return mode, assign_tiers(names)

    if mode == RoutingMode.SESSION_CUSTOM:
        names = model_names or DEFAULT_MODELS_WITH_CODER
        session = configure(
            vram_gb=vram_gb,
            profile=profile,
            quant=quant,
            models=names,
            tiers=_custom_tier_map(),
        )
        return mode, session

    if mode == RoutingMode.SESSION_MODELS:
        names = model_names or DEFAULT_MODELS
        session = configure(
            vram_gb=vram_gb,
            profile=profile,
            quant=quant,
            models=names,
        )
        return mode, session

    session = configure(vram_gb=vram_gb, profile=profile, quant=quant)
    return mode, session


def route_step(
    prompt: str,
    *,
    hint: str | None,
    mode: RoutingMode,
    explicit_tiers,
) -> object:
    if mode == RoutingMode.EXPLICIT:
        assert explicit_tiers is not None
        return explain_route(prompt, explicit_tiers, hint=hint)
    return explain(prompt, hint=hint)


def run_agent_loop(
    *,
    steps: tuple[AgentStep, ...] = DEFAULT_STEPS,
    mode: RoutingMode = RoutingMode.SESSION_PRESET,
    model_names: list[str] | None = None,
    base_url: str = "http://127.0.0.1:11434",
    dry_run: bool = True,
    timeout_seconds: int = 90,
    profile: str | None = "workstation_16gb",
    vram_gb: int | None = 16,
    quant: str | None = "qat",
    verbose: bool = False,
) -> list[StepResult]:
    mode, routing_ctx = setup_routing(
        mode,
        profile=profile,
        vram_gb=vram_gb,
        quant=quant,
        model_names=model_names,
    )

    if verbose and mode != RoutingMode.EXPLICIT:
        session = get_session()
        assert session is not None
        print(f"Mode: {mode.value}", flush=True)
        print(describe_session(), flush=True)
        if session.warnings:
            print("Session warnings:", flush=True)
            for line in session.warnings:
                print(f"  ! {_safe(line)}", flush=True)

    results: list[StepResult] = []

    for index, step in enumerate(steps, start=1):
        decision = route_step(
            step.prompt,
            hint=step.hint,
            mode=mode,
            explicit_tiers=routing_ctx if mode == RoutingMode.EXPLICIT else None,
        )
        tier, model = decision.tier, decision.model
        reasons = list(decision.reasons)

        latency_ms: int | None = None
        preview = ""
        skipped = dry_run

        if dry_run:
            preview = f"[dry-run step {index}] would call {model}"
        else:
            start = time.perf_counter()
            text = generate_text(
                model,
                prompt=step.prompt,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            preview = text[:160].replace("\n", " ")

        results.append(
            StepResult(
                step=step.name,
                tier=tier.value,
                model=model,
                hint=step.hint,
                reasons=reasons,
                latency_ms=latency_ms,
                preview=preview,
                skipped_inference=skipped,
            )
        )
        print(
            f"[step {index}/{len(steps)}] {step.name}: tier={tier.value} model={model}"
            + (f" hint={step.hint}" if step.hint else ""),
            flush=True,
        )
        if verbose:
            for reason in reasons:
                print(f"  - {_safe(reason)}", flush=True)
        if latency_ms is not None:
            print(f"  latency_ms={latency_ms} preview={preview!r}", flush=True)

    return results


def _resolve_mode(args: argparse.Namespace) -> RoutingMode:
    if args.explicit or args.no_session:
        return RoutingMode.EXPLICIT
    if args.custom_tiers:
        return RoutingMode.SESSION_CUSTOM
    if args.models:
        return RoutingMode.SESSION_MODELS
    return RoutingMode.SESSION_PRESET


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent runner POC: configure() + route() per step (or explicit tiers)",
    )
    parser.add_argument("--live", action="store_true", help="Call Ollama for each step (slow)")
    parser.add_argument("--json", action="store_true", help="Print JSON results")
    parser.add_argument("--verbose", action="store_true", help="Print session + explain reasons")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--profile", default=os.environ.get("SPLIT_STACK_PROFILE") or "workstation_16gb")
    parser.add_argument(
        "--vram-gb",
        type=int,
        default=int(os.environ.get("SPLIT_STACK_VRAM_GB", "16") or 16),
    )
    parser.add_argument("--quant", default=os.environ.get("SPLIT_STACK_QUANT") or "qat")
    parser.add_argument(
        "--models",
        help="Comma-separated models (session level 1, or explicit with --explicit)",
    )
    parser.add_argument(
        "--custom-tiers",
        action="store_true",
        help="Session level 2: pin code slot to deepseek-coder:6.7b",
    )
    parser.add_argument(
        "--explicit",
        action="store_true",
        help="Level 3: assign_tiers + explain_route (no session)",
    )
    parser.add_argument(
        "--no-session",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [part.strip() for part in args.models.split(",") if part.strip()]

    mode = _resolve_mode(args)
    results = run_agent_loop(
        model_names=model_names,
        base_url=args.base_url,
        dry_run=not args.live,
        profile=args.profile,
        vram_gb=args.vram_gb,
        quant=args.quant,
        mode=mode,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps([asdict(item) for item in results], indent=2))

    if not args.live:
        print("\nDry run only (routing). Re-run with --live to measure Ollama latency per step.")
        print("See patterns.py for all four API levels side by side.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
