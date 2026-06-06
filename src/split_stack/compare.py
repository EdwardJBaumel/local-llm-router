"""Side-by-side compare: split-stack routing vs always-largest baseline."""

from __future__ import annotations

import time
from dataclasses import dataclass

from split_stack.model_registry import load_registry, model_weight
from split_stack.poc_models import DEFAULT_POC_STACK
from split_stack.routing import route_prompt
from split_stack.tiering import assign_tiers

DEFAULT_MODELS = list(DEFAULT_POC_STACK)


class CompareRunError(RuntimeError):
    """Live compare failed on a specific agent step."""

    def __init__(self, step: str, model: str, message: str) -> None:
        self.step = step
        self.model = model
        super().__init__(f"Failed on step '{step}' (model {model}): {message}")


@dataclass(frozen=True)
class CompareStep:
    name: str
    prompt: str
    hint: str | None = None


DEFAULT_STEPS: tuple[CompareStep, ...] = (
    CompareStep("understand_goal", "Summarise the user goal: add auth to a Flask API", "explain"),
    CompareStep("quick_lookup", "what is JWT in one sentence?", "lookup"),
    CompareStep("compare_options", "compare session cookies vs JWT for a small SaaS API", "explain"),
    CompareStep("design", "design a webhook retry strategy with idempotency keys", "design"),
    CompareStep("reason", "prove this token expiry policy step by step", "reason"),
)


@dataclass(frozen=True)
class CompareRow:
    step: str
    routed_tier: str
    routed_model: str
    baseline_model: str
    routed_latency_ms: int | None = None
    baseline_latency_ms: int | None = None


@dataclass(frozen=True)
class CompareSummary:
    baseline_model: str
    routed_models_used: int
    baseline_models_used: int
    steps_avoided_largest: int
    total_steps: int
    routed_total_latency_ms: int | None = None
    baseline_total_latency_ms: int | None = None


@dataclass(frozen=True)
class CompareReport:
    models: tuple[str, ...]
    rows: tuple[CompareRow, ...]
    summary: CompareSummary


def largest_model(model_names: list[str]) -> str:
    registry = load_registry()
    return max(model_names, key=lambda name: model_weight(name, registry))


def _build_summary(rows: tuple[CompareRow, ...], baseline_model: str) -> CompareSummary:
    routed_models = {row.routed_model for row in rows}
    avoided = sum(1 for row in rows if row.routed_model != row.baseline_model)
    routed_latency = None
    baseline_latency = None
    if rows and rows[0].routed_latency_ms is not None:
        routed_latency = sum(row.routed_latency_ms or 0 for row in rows)
        baseline_latency = sum(row.baseline_latency_ms or 0 for row in rows)
    return CompareSummary(
        baseline_model=baseline_model,
        routed_models_used=len(routed_models),
        baseline_models_used=1,
        steps_avoided_largest=avoided,
        total_steps=len(rows),
        routed_total_latency_ms=routed_latency,
        baseline_total_latency_ms=baseline_latency,
    )


def run_compare(
    *,
    steps: tuple[CompareStep, ...] = DEFAULT_STEPS,
    model_names: list[str] | None = None,
    base_url: str = "http://127.0.0.1:11434",
    dry_run: bool = True,
    timeout_seconds: int = 90,
) -> CompareReport:
    models = model_names or list(DEFAULT_MODELS)
    tiers = assign_tiers(models)
    baseline = largest_model(models)
    rows: list[CompareRow] = []

    generate_text = None
    if not dry_run:
        from split_stack.ollama_generate import generate_text as _generate_text

        generate_text = _generate_text

    for step in steps:
        tier, routed_model = route_prompt(step.prompt, tiers, hint=step.hint)
        routed_latency_ms: int | None = None
        baseline_latency_ms: int | None = None

        if generate_text is not None:
            try:
                start = time.perf_counter()
                generate_text(
                    routed_model,
                    step.prompt,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                )
                routed_latency_ms = int((time.perf_counter() - start) * 1000)

                start = time.perf_counter()
                generate_text(
                    baseline,
                    step.prompt,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                )
                baseline_latency_ms = int((time.perf_counter() - start) * 1000)
            except RuntimeError as exc:
                active_model = routed_model if routed_latency_ms is None else baseline
                raise CompareRunError(step.name, active_model, str(exc)) from exc

        rows.append(
            CompareRow(
                step=step.name,
                routed_tier=tier.value,
                routed_model=routed_model,
                baseline_model=baseline,
                routed_latency_ms=routed_latency_ms,
                baseline_latency_ms=baseline_latency_ms,
            )
        )

    row_tuple = tuple(rows)
    return CompareReport(
        models=tuple(models),
        rows=row_tuple,
        summary=_build_summary(row_tuple, baseline),
    )


def format_compare_text(report: CompareReport) -> str:
    baseline = report.summary.baseline_model
    lines = [
        f"Compare: split-stack vs always-largest ({baseline})",
        "",
        f"{'step':<18} | {'routed tier':<12} | {'routed model':<12} | baseline model",
    ]
    for row in report.rows:
        lines.append(
            f"{row.step:<18} | {row.routed_tier:<12} | {row.routed_model:<12} | {row.baseline_model}"
        )
        if row.routed_latency_ms is not None:
            lines.append(
                f"  routed_latency_ms={row.routed_latency_ms} "
                f"baseline_latency_ms={row.baseline_latency_ms}"
            )

    summary = report.summary
    lines.extend(
        [
            "",
            "Summary:",
            f"  split-stack:  {summary.routed_models_used} models used, "
            f"{summary.steps_avoided_largest}/{summary.total_steps} steps avoided largest",
            f"  baseline:     {summary.baseline_models_used} model used, "
            f"{summary.total_steps}/{summary.total_steps} on largest",
        ]
    )
    if summary.routed_total_latency_ms is not None:
        lines.append(
            f"  routed total latency:   {summary.routed_total_latency_ms} ms"
        )
        lines.append(
            f"  baseline total latency: {summary.baseline_total_latency_ms} ms"
        )
    return "\n".join(lines)
