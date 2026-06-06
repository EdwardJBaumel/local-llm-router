from local_llm_router.models import ComplexityTier, StepKind, TierMap
from local_llm_router.routing import route_prompt


def test_route_prompt_returns_tier_and_model():
    tiers = TierMap(
        simple="qwen3:4b",
        medium="qwen3:8b",
        complex="qwen3:14b",
        reasoning="qwen3:30b-a3b",
    )
    tier, model = route_prompt("what is caching?", tiers)
    assert tier == ComplexityTier.SIMPLE
    assert model == "qwen3:4b"


def test_route_prompt_uses_step_hint():
    tiers = TierMap(
        simple="gemma4:e4b",
        medium="qwen3:8b",
        complex="qwen3:14b",
        reasoning="deepseek-r1:8b",
    )
    tier, model = route_prompt("anything verbose here", tiers, hint="lookup")
    assert tier == ComplexityTier.SIMPLE
    assert model == "gemma4:e4b"


def test_route_prompt_uses_code_specialist():
    tiers = TierMap(
        simple="gemma4:e4b",
        medium="qwen3:8b",
        complex="qwen3:14b",
        reasoning="qwen3:14b",
        code="deepseek-coder:6.7b",
    )
    tier, model = route_prompt("refactor this auth module for testability", tiers)
    assert tier == ComplexityTier.COMPLEX
    assert model == "deepseek-coder:6.7b"


def test_route_prompt_code_hint():
    tiers = TierMap(
        simple="gemma4:e4b",
        medium="qwen3:8b",
        complex="qwen3:14b",
        reasoning="qwen3:14b",
        code="deepseek-coder:6.7b",
    )
    tier, model = route_prompt("hello", tiers, hint=StepKind.CODE)
    assert tier == ComplexityTier.COMPLEX
    assert model == "deepseek-coder:6.7b"
