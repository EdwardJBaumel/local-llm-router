import pytest

from local_llm_router.tiering import assign_tiers


def test_assign_tiers_basic_ordering():
    tiers = assign_tiers(["qwen3:8b", "qwen3:14b", "qwen3:4b"])
    assert tiers.simple == "qwen3:4b"
    assert tiers.complex == "qwen3:14b"


def test_assign_tiers_requires_models():
    with pytest.raises(ValueError):
        assign_tiers([])
