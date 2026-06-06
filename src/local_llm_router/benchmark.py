"""Fixed prompt suite for routing benchmarks (no inference required)."""

from __future__ import annotations

from dataclasses import dataclass

from local_llm_router.poc_models import DEFAULT_POC_STACK
from local_llm_router.routing import route_prompt
from local_llm_router.tiering import assign_tiers


@dataclass(frozen=True)
class BenchmarkPrompt:
    id: str
    prompt: str
    note: str


DEFAULT_MODELS = list(DEFAULT_POC_STACK) + ["deepseek-r1:8b", "qwen2.5-coder:7b"]

BENCHMARK_PROMPTS: tuple[BenchmarkPrompt, ...] = (
    BenchmarkPrompt("b01", "what is caching?", "definition"),
    BenchmarkPrompt("b02", "what is an API?", "definition"),
    BenchmarkPrompt("b03", "define idempotency in one paragraph", "short explain"),
    BenchmarkPrompt("b04", "explain eventual consistency for a junior dev", "medium explain"),
    BenchmarkPrompt("b05", "compare Redis vs Memcached for session storage", "compare"),
    BenchmarkPrompt("b06", "outline a plan for adding logging to a Flask app", "plan"),
    BenchmarkPrompt("b07", "debug why webhook retries duplicate orders", "debug keyword"),
    BenchmarkPrompt("b08", "design a distributed retry strategy for webhooks", "architecture"),
    BenchmarkPrompt("b09", "refactor this auth module for testability", "refactor keyword"),
    BenchmarkPrompt("b10", "prove this retry policy step by step with edge cases", "reasoning"),
)


@dataclass(frozen=True)
class BenchmarkRow:
    id: str
    prompt: str
    tier: str
    model: str
    note: str


@dataclass(frozen=True)
class BenchmarkReport:
    models: tuple[str, ...]
    rows: tuple[BenchmarkRow, ...]

    @property
    def tier_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.rows:
            counts[row.tier] = counts.get(row.tier, 0) + 1
        return counts


def run_benchmark(
    model_names: list[str] | None = None,
) -> BenchmarkReport:
    models = model_names or list(DEFAULT_MODELS)
    tiers = assign_tiers(models)
    rows: list[BenchmarkRow] = []
    for item in BENCHMARK_PROMPTS:
        tier, model = route_prompt(item.prompt, tiers)
        rows.append(
            BenchmarkRow(
                id=item.id,
                prompt=item.prompt,
                tier=tier.value,
                model=model,
                note=item.note,
            )
        )
    return BenchmarkReport(models=tuple(models), rows=tuple(rows))


def format_markdown_table(report: BenchmarkReport) -> str:
    lines = [
        "| id | tier | model | note |",
        "| --- | --- | --- | --- |",
    ]
    for row in report.rows:
        lines.append(f"| {row.id} | {row.tier} | {row.model} | {row.note} |")
    return "\n".join(lines)


def naive_single_model(report: BenchmarkReport) -> str:
    """Largest model in tier map (simulates always-use-biggest policy)."""
    tiers = assign_tiers(list(report.models))
    return tiers.complex


def routed_model_mix(report: BenchmarkReport) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in report.rows:
        counts[row.model] = counts.get(row.model, 0) + 1
    return counts
