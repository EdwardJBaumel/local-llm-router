import pytest

from split_stack.model_registry import (
    infer_model_profile,
    load_registry,
    normalize_deployment_profile,
    resolve_discovered_models,
)
from split_stack.tiering import assign_tiers


def test_gemma4_e4b_gets_sensible_weight():
    profile = infer_model_profile("gemma4:e4b")
    assert profile.weight == 4000
    assert profile.family == "gemma"
    assert profile.source == "registry"


def test_qwen3_moe_gets_registry_weight():
    profile = infer_model_profile("qwen3:30b-a3b")
    assert profile.weight == 30000
    assert profile.source == "registry"


def test_phi3_mini_gets_registry_weight():
    profile = infer_model_profile("phi3:mini")
    assert profile.weight == 3800
    assert profile.family == "phi"
    assert profile.source == "registry"


def test_unknown_model_uses_heuristic():
    profile = infer_model_profile("custom:9b-test")
    assert profile.weight == 9000
    assert profile.vram_gb == 9
    assert profile.source == "heuristic"


def test_assign_tiers_ranks_gemma_and_qwen():
    tiers = assign_tiers(["qwen3:14b", "gemma4:e4b", "qwen3:4b"])
    assert tiers.simple == "gemma4:e4b"
    assert tiers.complex == "qwen3:14b"


def test_custom_config_overrides(tmp_path):
    config = tmp_path / "split-stack.models.json"
    config.write_text(
        """
        {
          "assumed_vram_gb": 8,
          "models": [
            {"match": "my-tiny", "weight": 1000, "vram_gb": 2, "family": "custom"},
            {"match": "my-big", "weight": 9000, "vram_gb": 7, "family": "custom"}
          ]
        }
        """,
        encoding="utf-8",
    )
    registry = load_registry(str(config))
    tiers = assign_tiers(["my-big", "my-tiny"], registry=registry)
    assert tiers.simple == "my-tiny"
    assert tiers.complex == "my-big"
    profile = infer_model_profile("my-big", registry)
    assert profile.vram_ok is True


def test_workstation_profile_sets_assumed_vram():
    registry = load_registry(profile="workstation_8gb")
    assert registry.profile == "workstation_8gb"
    assert registry.assumed_vram_gb == 8
    assert registry.apply_vram_filter is True
    profile = infer_model_profile("qwen3:30b", registry)
    assert profile.vram_ok is False


def test_datacenter_profile_skips_vram_filter():
    registry = load_registry(profile="datacenter")
    assert registry.profile == "datacenter"
    assert registry.assumed_vram_gb is None
    assert registry.apply_vram_filter is False
    profile = infer_model_profile("qwen3:30b", registry)
    assert profile.vram_ok is True


def test_datacenter_config_from_file(tmp_path):
    config = tmp_path / "split-stack.models.json"
    config.write_text(
        """
        {
          "deployment_profile": "datacenter",
          "models": [
            {"match": "fleet-small", "weight": 1000, "family": "custom"},
            {"match": "fleet-large", "weight": 9000, "family": "custom"}
          ]
        }
        """,
        encoding="utf-8",
    )
    registry = load_registry(str(config))
    resolved = resolve_discovered_models(
        ["fleet-small", "fleet-large", "unknown:70b"],
        registry=registry,
        only_vram_ok=True,
    )
    assert len(resolved) == 3
    assert all(item.vram_ok for item in resolved)


def test_profile_aliases():
    assert normalize_deployment_profile("12gb") == "workstation_12gb"
    assert normalize_deployment_profile("32gb") == "workstation_32gb"
    assert normalize_deployment_profile("datacenter") == "datacenter"


def test_workstation_32gb_profile():
    registry = load_registry(profile="workstation_32gb")
    assert registry.profile == "workstation_32gb"
    assert registry.assumed_vram_gb == 32
    assert infer_model_profile("qwen3:30b", registry).vram_ok is True
    assert infer_model_profile("llama3.1:70b", registry).vram_ok is False


def test_unknown_profile_raises():
    with pytest.raises(ValueError, match="Unknown deployment profile"):
        normalize_deployment_profile("cloud_9000")
