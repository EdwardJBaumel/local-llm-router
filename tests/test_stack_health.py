from unittest.mock import patch

from split_stack.discovery import ModelInventory
from split_stack.stack_health import ModelTagInfo, check_stack_health, format_stack_health


def test_check_stack_health_all_present():
    inventory = ModelInventory(
        api_models=("gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b"),
        disk_models=("gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b"),
        manifest_roots=("/models",),
        suggested_stack=("gemma4:e4b", "qwen3:8b", "qwen3:14b"),
        note=None,
    )
    with patch("split_stack.stack_health.list_model_inventory", return_value=inventory):
        with patch(
            "split_stack.stack_health.audit_model_folders",
            return_value={"duplicate_tags": []},
        ):
            report = check_stack_health(profile="workstation_12gb", quant="default")
    assert report.ready is True
    assert report.missing == ()
    assert "gemma4:e4b" in report.resolved
    codes = {item.code for item in report.findings}
    assert "stack_complete" in codes
    assert "routing_spread" not in codes


def test_check_stack_health_missing_and_routing_blocked():
    inventory = ModelInventory(
        api_models=("qwen3:8b",),
        disk_models=("qwen3:8b",),
        manifest_roots=("/models",),
        suggested_stack=("qwen3:8b",),
        note=None,
    )
    with patch("split_stack.stack_health.list_model_inventory", return_value=inventory):
        with patch(
            "split_stack.stack_health.audit_model_folders",
            return_value={"duplicate_tags": []},
        ):
            report = check_stack_health(profile="workstation_12gb", quant="default")
    assert report.ready is False
    assert "gemma4:e4b" in report.missing
    codes = {item.code for item in report.findings}
    assert "missing" in codes
    assert "routing_spread" in codes


def test_check_stack_health_duplicate_tags_warn():
    inventory = ModelInventory(
        api_models=("gemma4:e4b", "qwen3:8b", "qwen3:14b"),
        disk_models=("gemma4:e4b", "qwen3:8b", "qwen3:14b"),
        manifest_roots=("/a", "/b"),
        suggested_stack=("gemma4:e4b", "qwen3:8b", "qwen3:14b"),
        note=None,
    )
    with patch("split_stack.stack_health.list_model_inventory", return_value=inventory):
        with patch(
            "split_stack.stack_health.audit_model_folders",
            return_value={"duplicate_tags": ["qwen3:8b"]},
        ):
            report = check_stack_health(vram_gb=16, quant="qat")
    assert any(item.code == "duplicate_tags" for item in report.findings)
    assert report.profile == "workstation_16gb"


def test_format_stack_health_includes_routing_line():
    inventory = ModelInventory(
        api_models=("qwen3:8b",),
        disk_models=(),
        manifest_roots=(),
        suggested_stack=("qwen3:8b",),
        note="Ollama API unreachable.",
    )
    with patch("split_stack.stack_health.list_model_inventory", return_value=inventory):
        with patch(
            "split_stack.stack_health.audit_model_folders",
            return_value={"duplicate_tags": []},
        ):
            report = check_stack_health(profile="workstation_12gb")
    text = format_stack_health(report)
    assert "Stack health" in text
    assert "Routing: not ready" in text
    assert "Ollama API unreachable" in text


def test_quant_mismatch_warns_library_gemma_with_qat_mode():
    inventory = ModelInventory(
        api_models=("gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b"),
        disk_models=(),
        manifest_roots=(),
        suggested_stack=(),
        note=None,
    )
    tag_info = {
        "gemma4:e4b": ModelTagInfo(
            name="gemma4:e4b",
            size_bytes=9_608_350_718,
            quantization_level="Q4_K_M",
        ),
    }
    with patch("split_stack.stack_health.list_model_inventory", return_value=inventory):
        with patch(
            "split_stack.stack_health.audit_model_folders",
            return_value={"duplicate_tags": []},
        ):
            with patch("split_stack.stack_health._fetch_ollama_tag_info", return_value=tag_info):
                report = check_stack_health(profile="workstation_12gb", quant="qat")
    codes = {item.code for item in report.findings}
    assert "quant_mismatch" in codes
    assert any("gemma4:e4b" in item.message for item in report.findings)
