from pathlib import Path
from unittest.mock import patch

from local_llm_router.setup_wizard import (
    model_is_installed,
    plan_setup,
    run_setup,
    write_setup_config,
)


def test_model_is_installed_matches_tag_prefix():
    installed = ["qwen3:4b", "gemma4:e4b:latest"]
    assert model_is_installed("qwen3:4b", installed)
    assert model_is_installed("gemma4:e4b", installed)
    assert not model_is_installed("qwen3:14b", installed)


@patch("local_llm_router.setup_wizard.discover_models", return_value=["gemma4:e4b", "qwen3:8b"])
def test_plan_setup_reports_missing(_mock_discover):
    plan = plan_setup("workstation_12gb", config_path=Path("test-config.json"))
    assert plan.profile == "workstation_12gb"
    assert "gemma4:e4b" in plan.installed
    assert "qwen3:14b" in plan.missing


@patch("local_llm_router.setup_wizard.pull_model")
@patch("local_llm_router.setup_wizard.discover_models", return_value=[])
def test_run_setup_pulls_and_writes_config(_mock_discover, mock_pull, tmp_path):
    config = tmp_path / "local-llm-router.models.json"
    result = run_setup(
        "workstation_8gb",
        config_path=config,
        assume_yes=True,
        interactive=False,
    )
    assert result.ready
    assert mock_pull.call_count == 3
    assert config.is_file()
    assert '"deployment_profile": "workstation_8gb"' in config.read_text(encoding="utf-8")


@patch("local_llm_router.setup_wizard.discover_models", return_value=["gemma4:e4b", "qwen3:8b", "qwen3:14b", "deepseek-r1:8b"])
def test_run_setup_dry_run_no_pull(_mock_discover, tmp_path):
    config = tmp_path / "local-llm-router.models.json"
    result = run_setup(
        "workstation_12gb",
        config_path=config,
        dry_run=True,
        interactive=False,
    )
    assert result.ready
    assert result.dry_run
    assert result.tiers["simple"] == "gemma4:e4b"
    assert not config.is_file()


def test_write_setup_config_sets_profile(tmp_path):
    path = tmp_path / "local-llm-router.models.json"
    write_setup_config("workstation_24gb", path)
    text = path.read_text(encoding="utf-8")
    assert "workstation_24gb" in text
