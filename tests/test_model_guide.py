from split_stack.model_guide import build_model_guide


def test_build_model_guide_routes_hints_to_stack():
    guide = build_model_guide(
        ["gemma4:e4b", "qwen3:8b", "qwen3:14b"],
        pool=["gemma4:e4b", "qwen3:8b", "qwen3:14b", "phi4-reasoning:14b"],
    )
    assert guide.tiers["simple"] == "gemma4:e4b"
    assert guide.tiers["medium"] == "qwen3:8b"
    assert guide.tiers["complex"] == "qwen3:14b"

    by_hint = {item.hint_id: item for item in guide.hint_routes}
    assert by_hint["lookup"].model == "gemma4:e4b"
    assert by_hint["explain"].model == "qwen3:8b"
    assert by_hint["design"].model == "qwen3:14b"

    in_stack = [card for card in guide.models if card.in_stack]
    assert len(in_stack) == 3
    phi = next(card for card in guide.models if card.name == "phi4-reasoning:14b")
    assert not phi.in_stack
    assert "reason" in phi.best_for.lower() or "reasoning" in phi.best_for.lower()


def test_reasoning_model_in_stack_gets_reason_hint():
    guide = build_model_guide(
        ["gemma4:e4b", "qwen3:8b", "phi4-reasoning:14b"],
    )
    assert guide.tiers["reasoning"] == "phi4-reasoning:14b"
    reason = next(item for item in guide.hint_routes if item.hint_id == "reason")
    assert reason.model == "phi4-reasoning:14b"
