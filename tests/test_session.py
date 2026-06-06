import os

import pytest

from local_llm_router.models import TierMap
from local_llm_router.session import (
    configure,
    profile_for_vram_gb,
    reset_session_for_tests,
    route,
)


@pytest.fixture(autouse=True)
def _clean_session(monkeypatch):
    reset_session_for_tests()
    monkeypatch.delenv("local_llm_router_VRAM_GB", raising=False)
    monkeypatch.delenv("local_llm_router_PROFILE", raising=False)
    yield
    reset_session_for_tests()


def test_profile_for_vram_gb_buckets():
    assert profile_for_vram_gb(8) == "workstation_8gb"
    assert profile_for_vram_gb(16) == "workstation_16gb"
    assert profile_for_vram_gb(24) == "workstation_24gb"


def test_configure_with_explicit_models():
    session = configure(vram_gb=16, models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    assert session.profile == "workstation_16gb"
    assert session.vram_gb == 16
    tier, model = route("what is JWT?", hint="lookup")
    assert tier.value == "simple"
    assert model == "gemma4:e4b"


def test_configure_from_env(monkeypatch):
    monkeypatch.setenv("local_llm_router_VRAM_GB", "16")
    configure(models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    tier, model = route("compare options", hint="explain")
    assert model == "qwen3:8b"


def test_route_without_configure_raises():
    with pytest.raises(RuntimeError, match="configure"):
        route("hello")


def test_configure_with_custom_tiers():
    session = configure(
        vram_gb=16,
        models=["gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-coder:6.7b"],
        tiers=TierMap(
            simple="gemma4:e4b",
            medium="qwen3:8b",
            complex="qwen3:14b",
            reasoning="qwen3:14b",
            code="deepseek-coder:6.7b",
        ),
    )
    assert session.tiers.code == "deepseek-coder:6.7b"
    tier, model = route("fix this bug", hint="code")
    assert model == "deepseek-coder:6.7b"


def test_configure_rejects_tiers_not_in_models():
    with pytest.raises(ValueError, match="not in models="):
        configure(
            vram_gb=16,
            models=["gemma4:e4b", "qwen3:8b", "qwen3:14b"],
            tiers=TierMap(
                simple="gemma4:e4b",
                medium="qwen3:8b",
                complex="qwen3:14b",
                reasoning="qwen3:14b",
                code="deepseek-coder:6.7b",
            ),
        )
