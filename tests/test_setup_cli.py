import json
from pathlib import Path
from unittest.mock import patch

from split_stack.cli import main
from split_stack.setup_wizard import SetupResult


@patch("split_stack.cli.run_setup")
def test_stack_setup_json(mock_run_setup, capsys):
    mock_run_setup.return_value = SetupResult(
        profile="workstation_12gb",
        config_path=Path("split-stack.models.json"),
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
