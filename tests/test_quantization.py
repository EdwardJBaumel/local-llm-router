import pytest

from local_llm_router.model_registry import infer_model_profile, load_registry
from local_llm_router.presets import recommended_models
from local_llm_router.quantization import (
    adjust_vram_for_quant,
    expand_models_for_quant,
    normalize_quant_mode,
)
from local_llm_router.session import configure, reset_session_for_tests


def test_normalize_quant_mode_aliases():
    assert normalize_quant_mode(None) == "default"
    assert normalize_quant_mode("qat") == "qat"
    assert normalize_quant_mode("q4") == "qat"
    assert normalize_quant_mode("mobile") == "qat_mobile"


def test_normalize_quant_mode_invalid():
    with pytest.raises(ValueError, match="Unknown quant"):
        normalize_quant_mode("q3")


def test_qat_adjusts_gemma4_e4b_vram():
    base = infer_model_profile("gemma4:e4b")
    assert base.vram_gb == 4
    qat = infer_model_profile("gemma4:e4b", quant_mode="qat")
    assert qat.vram_gb == 5
    assert qat.quant_mode == "qat"


def test_qat_makes_26b_a4b_fit_16gb_profile():
    from local_llm_router.model_registry import ModelRegistry, _entries_from_raw, _BUILTIN_RAW

    reg = ModelRegistry(
        profile="workstation_16gb",
        assumed_vram_gb=16,
        apply_vram_filter=True,
        entries=_entries_from_raw(_BUILTIN_RAW),
    )
    profile = infer_model_profile("gemma4:26b-a4b", reg, quant_mode="default")
    assert profile.vram_ok is False
    qat = infer_model_profile("gemma4:26b-a4b", reg, quant_mode="qat")
    assert qat.vram_gb == 15
    assert qat.vram_ok is True
    assert qat.source == "registry"


def test_qat_weight_unchanged():
    """Quant adjusts VRAM only — routing weight must stay the same."""
    base = infer_model_profile("gemma4:26b-a4b")
    qat = infer_model_profile("gemma4:26b-a4b", quant_mode="qat")
    assert base.weight == qat.weight == 26000


def test_qat_expands_16gb_stack():
    base = recommended_models("workstation_16gb")
    qat = recommended_models("workstation_16gb", quant="qat")
    assert "gemma4:26b-a4b" not in base
    assert "gemma4:26b-a4b" in qat


def test_configure_with_quant(monkeypatch):
    reset_session_for_tests()
    monkeypatch.delenv("local_llm_router_VRAM_GB", raising=False)
    session = configure(vram_gb=16, quant="qat", models=["gemma4:e4b", "qwen3:8b", "gemma4:26b-a4b"])
    assert session.quant == "qat"
    assert "gemma4:26b-a4b" in session.models
