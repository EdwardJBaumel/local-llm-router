import json
from pathlib import Path
from unittest.mock import patch

from local_llm_router.cli import main
from local_llm_router.setup_wizard import SetupResult


@patch("local_llm_router.cli.run_setup")
def test_stack_setup_json(mock_run_setup, capsys):
    mock_run_setup.return_value = SetupResult(
        profile="workstation_12gb",
        config_path=Path("local-llm-router.models.json"),
        pulled=("qwen3:14b",),
        skipped=(),
        already_present=("gemma4:e4b", "qwen3:8b"),
        tiers={
            "simple": "gemma4:e4b",
            "medium": "qwen3:8b",
            "complex": "qwen3:14b",
            "reasoning": "deepseek-r1:8b",
            "code": None,
        },
    )
    exit_code = main(["setup", "--profile", "12gb", "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["profile"] == "workstation_12gb"
    assert "qwen3:14b" in payload["pulled"]


def test_stack_doctor_check_stack_json(capsys):
    from local_llm_router.discovery import ModelInventory

    inventory = ModelInventory(
        api_models=("gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b", "gemma4:26b-a4b"),
        disk_models=(),
        manifest_roots=(),
        suggested_stack=("gemma4:e4b", "qwen3:8b", "qwen3:14b"),
        note=None,
    )
    with patch("local_llm_router.stack_health.list_model_inventory", return_value=inventory):
        with patch(
            "local_llm_router.stack_health.audit_model_folders",
            return_value={"duplicate_tags": []},
        ):
            exit_code = main(["doctor", "--check-stack", "--vram-gb", "16", "--quant", "qat", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["profile"] == "workstation_16gb"
    assert payload["quant"] == "qat"
