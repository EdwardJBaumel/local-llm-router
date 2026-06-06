"""Four integration patterns — same agent step, increasing control.

Run from repo root::

    python examples/agent_runner/patterns.py

See also: docs/INTEGRATION.md
"""

from __future__ import annotations

from local_llm_router import (
    TierMap,
    assign_tiers,
    configure,
    describe_session,
    explain,
    explain_route,
    route,
    route_prompt,
)
from local_llm_router.session import reset_session_for_tests

PROMPT = "what is JWT in one sentence?"
HINT = "lookup"
MODELS = ["gemma4:e4b", "qwen3:8b", "qwen3:14b"]
MODELS_WITH_CODER = [*MODELS, "deepseek-coder:6.7b"]


def _banner(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _safe(text: str) -> str:
    return text.replace("\u2192", "->").replace("\u2014", "-")


def _print_decision(label: str, decision) -> None:
    print(f"{label}: tier={decision.tier.value} model={decision.model}")
    for reason in decision.reasons[:2]:
        print(f"  - {_safe(reason)}")


def level0_session_preset() -> None:
    """Trust the 16 GB preset — one line setup."""
    reset_session_for_tests()
    configure(vram_gb=16, quant="qat")
    decision = explain(PROMPT, hint=HINT)
    _print_decision("Level 0 (preset)", decision)


def level1_session_explicit_models() -> None:
    """Pin model tags; tiers auto-assigned from weights."""
    reset_session_for_tests()
    configure(vram_gb=16, quant="qat", models=MODELS)
    tier, model = route(PROMPT, hint=HINT)
    print(f"Level 1 (models=): tier={tier.value} model={model}")
    print("  session:", describe_session()["tiers"])


def level2_session_custom_tiers() -> None:
    """Pin tier slots — e.g. dedicated code model."""
    reset_session_for_tests()
    configure(
        vram_gb=16,
        models=MODELS_WITH_CODER,
        tiers=TierMap(
            simple="gemma4:e4b",
            medium="qwen3:8b",
            complex="qwen3:14b",
            reasoning="qwen3:14b",
            code="deepseek-coder:6.7b",
        ),
    )
    code_decision = explain("fix this asyncio bug", hint="code")
    _print_decision("Level 2 (custom tiers, code hint)", code_decision)


def level3_explicit_no_session() -> None:
    """No globals — gateways and unit tests."""
    tiers = assign_tiers(MODELS)
    decision = explain_route(PROMPT, tiers, hint=HINT)
    _print_decision("Level 3 (explicit)", decision)
    tier, model = route_prompt(PROMPT, tiers, hint=HINT)
    print(f"  route_prompt tuple: ({tier.value}, {model})")


def main() -> int:
    _banner("local-llm-router routing patterns (dry — no Ollama)")
    level0_session_preset()
    level1_session_explicit_models()
    level2_session_custom_tiers()
    level3_explicit_no_session()
    print("\nAgent loop body is always the same shape:")
    print("  decision = explain(step.prompt, hint=step.kind)  # or route()")
    print("  tier, model = decision.tier, decision.model")
    print("  response = your_client.generate(model=model, prompt=step.prompt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
