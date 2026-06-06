from split_stack.presets import assign_recommended_tiers, recommended_models
from split_stack.tiering import assign_tiers


def test_recommended_models_12gb():
    models = recommended_models("12gb")
    assert "gemma4:e4b" in models
    assert "deepseek-r1:8b" in models


def test_assign_recommended_tiers_32gb():
    tiers = assign_recommended_tiers("workstation_32gb")
    assert tiers.simple == "gemma4:e4b"
    assert tiers.complex == "qwen3:30b-a3b"
    assert tiers.reasoning == "deepseek-r1:8b"
    assert tiers.code == "deepseek-coder:6.7b"


def test_assign_recommended_tiers_16gb():
    tiers = assign_recommended_tiers("workstation_16gb")
    assert tiers.simple == "gemma4:e4b"
    assert tiers.medium == "qwen3:8b"
    assert tiers.complex == "qwen3:14b"
    assert tiers.reasoning == "deepseek-r1:8b"
    assert tiers.code is None


def test_assign_tiers_separates_code_and_reasoning():
    tiers = assign_tiers(
        [
            "gemma4:e4b",
            "qwen3:8b",
            "qwen3:14b",
            "deepseek-coder:6.7b",
            "deepseek-r1:8b",
        ]
    )
    assert tiers.simple == "gemma4:e4b"
    assert tiers.complex == "qwen3:14b"
    assert tiers.reasoning == "deepseek-r1:8b"
    assert tiers.code == "deepseek-coder:6.7b"
