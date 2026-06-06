from split_stack.community_picks import (
    build_community_guide,
    focus_stack,
    picks_for_hint,
    vram_tier_for_profile,
)
from split_stack.poc_models import models_for_preset


def test_vram_tier_for_12gb_profile():
    assert vram_tier_for_profile("workstation_12gb") == "M"


def test_picks_for_code_hint_m_tier():
    picks = picks_for_hint("code", vram_tier="M")
    models = [item.model for item in picks]
    assert "qwen3.5:27b" in models
    assert any(item.note for item in picks)


def test_focus_stack_agentic_m():
    stack = focus_stack("agentic", vram_tier="M")
    assert stack is not None
    assert stack.models == ("gemma4:e4b", "qwen3:8b", "qwen3:14b")


def test_community_preset_matches_focus_stack():
    models = models_for_preset("community_agentic", profile="workstation_12gb")
    assert models == ["gemma4:e4b", "qwen3:8b", "qwen3:14b"]


def test_build_community_guide_has_all_hints():
    guide = build_community_guide(profile="workstation_12gb")
    hint_ids = {item["hint_id"] for item in guide["hints"]}
    assert hint_ids == {"lookup", "explain", "design", "code", "reason"}
    assert guide["vram_tier"] == "M"
    assert guide["focus_stacks"]
