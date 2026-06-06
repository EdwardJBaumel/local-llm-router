import pytest

from local_llm_router import configure, explain, session_warnings
from local_llm_router.routing import explain_route
from local_llm_router.session import reset_session_for_tests
from local_llm_router.tiering import assign_tiers
from local_llm_router.validation import validate_tier_map


@pytest.fixture(autouse=True)
def _clean_session(monkeypatch):
    reset_session_for_tests()
    monkeypatch.delenv("local_llm_router_VRAM_GB", raising=False)
    monkeypatch.delenv("local_llm_router_PROFILE", raising=False)
    yield
    reset_session_for_tests()


def test_explain_route_with_hint():
    tiers = assign_tiers(["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    decision = explain_route("what is JWT?", tiers, hint="lookup")
    assert decision.model == "gemma4:e4b"
    assert decision.tier_source == "hint"
    assert decision.model_source == "tier_slot"
    assert any("hint=lookup" in reason for reason in decision.reasons)


def test_explain_route_code_fallback():
    tiers = assign_tiers(["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    decision = explain_route("refactor auth", tiers, hint="code")
    assert decision.model == "qwen3:14b"
    assert any("no code slot" in reason for reason in decision.reasons)


def test_configure_warnings_for_missing_specialists():
    session = configure(
        vram_gb=16,
        models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"],
    )
    assert session.warnings
    assert any("No code specialist" in line for line in session.warnings)
    assert any("No reasoning specialist" in line for line in session.warnings)


def test_session_explain():
    configure(vram_gb=16, models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    decision = explain("compare options", hint="explain")
    assert decision.model == "qwen3:8b"
    assert decision.to_dict()["tier"] == "medium"


def test_medium_is_second_smallest():
    tiers = assign_tiers(["gemma4:e4b", "qwen3:8b", "qwen3:14b", "qwen3:30b-a3b"])
    assert tiers.simple == "gemma4:e4b"
    assert tiers.medium == "qwen3:8b"
    assert tiers.complex == "qwen3:30b-a3b"


def test_validate_tier_map_detects_flat_reasoning():
    tiers = assign_tiers(["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    warnings = validate_tier_map(tiers, ["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    assert any("reason" in line.lower() for line in warnings)
