from split_stack.complexity import resolve_tier, score_prompt
from split_stack.hints import normalize_step_kind
from split_stack.models import ComplexityTier, StepKind


def test_score_prompt_reasoning_marker():
    assert score_prompt("prove this step by step") == ComplexityTier.REASONING


def test_score_prompt_simple_short_question():
    assert score_prompt("what is caching?") == ComplexityTier.SIMPLE


def test_score_prompt_complex_keyword():
    assert score_prompt("design architecture tradeoff for distributed retries") == ComplexityTier.COMPLEX


def test_resolve_tier_respects_hints():
    assert resolve_tier("anything", hint=StepKind.LOOKUP) == ComplexityTier.SIMPLE
    assert resolve_tier("anything", hint=StepKind.EXPLAIN) == ComplexityTier.MEDIUM
    assert resolve_tier("anything", hint=StepKind.DESIGN) == ComplexityTier.COMPLEX
    assert resolve_tier("anything", hint=StepKind.CODE) == ComplexityTier.COMPLEX
    assert resolve_tier("anything", hint=StepKind.REASON) == ComplexityTier.REASONING


def test_legacy_work_build_aliases():
    assert normalize_step_kind("work") == StepKind.EXPLAIN
    assert normalize_step_kind("build") == StepKind.DESIGN
