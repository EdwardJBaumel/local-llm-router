from split_stack.discovery import discover_models_from_disk, list_model_inventory, manifest_search_paths
from split_stack.hints import canonical_hint_id, list_hints, normalize_step_kind
from split_stack.models import StepKind
from split_stack.poc_models import models_for_preset, recommended_stack_for_vram, resolve_installed_stack, stack_payload


def test_hint_catalog_has_five_entries():
    assert len(list_hints()) == 5
    ids = [item["id"] for item in list_hints()]
    assert ids == ["lookup", "explain", "design", "code", "reason"]


def test_legacy_work_build_aliases():
    assert canonical_hint_id("work") == "explain"
    assert canonical_hint_id("build") == "design"
    assert normalize_step_kind("work") == StepKind.EXPLAIN


def test_default_poc_preset_uses_gemma_and_qwen():
    models = models_for_preset("mixed_12gb")
    assert models[0].startswith("gemma")
    assert "qwen3:8b" in models
    assert "qwen3:14b" in models


def test_resolve_installed_stack_falls_back():
    models, warning = resolve_installed_stack(["qwen3:8b"], preset_id="mixed_12gb")
    assert models == ["qwen3:8b"]
    assert warning is not None


def test_recommended_stack_for_vram_16gb_qat_adds_gemma26():
    stack = recommended_stack_for_vram(16, quant="qat")
    assert stack.profile == "workstation_16gb"
    assert "deepseek-r1:8b" in stack.models
    assert "gemma4:26b-a4b" in stack.models
    assert len(stack.models) > len(recommended_stack_for_vram(12, quant="qat").models)


def test_recommended_stack_16gb_is_superset_of_12gb():
    base_12 = set(recommended_stack_for_vram(12, quant="default").models)
    base_16 = set(recommended_stack_for_vram(16, quant="default").models)
    assert base_12 <= base_16


def test_stack_payload_vram_quant_keys():
    payload = stack_payload(vram_gb=16, quant="qat")
    assert payload["vram_gb"] == 16
    assert payload["quant"] == "qat"
    assert "gemma4:26b-a4b" in payload["models"]


def test_discover_models_from_disk_finds_user_layout():
    roots = manifest_search_paths()
    disk = discover_models_from_disk()
    # On dev machine with Tools/.ollama layout
    if any("Tools" in str(path) for path in roots):
        assert "qwen3:8b" in disk
        assert "gemma4:e4b" in disk


def test_list_model_inventory_merges_sources():
    inventory = list_model_inventory()
    merged = set(inventory.api_models) | set(inventory.disk_models)
    if inventory.disk_models:
        assert len(merged) >= len(inventory.api_models)
        assert len(inventory.suggested_stack) >= 2
