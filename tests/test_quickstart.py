import os
from pathlib import Path

from examples.quickstart import mini_app


def test_quickstart_tour_dry(capsys, monkeypatch):
    config = Path(__file__).resolve().parents[1] / "examples" / "quickstart" / "split-stack.models.json"
    monkeypatch.setenv("SPLIT_STACK_MODELS_CONFIG", str(config))
    exit_code = mini_app.main(["--tour"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "profile=workstation_12gb" in captured.out
    assert "Prompt routing (no inference)" in captured.out
    assert "model_mix:" in captured.out


def test_quickstart_single_prompt(capsys, monkeypatch):
    config = Path(__file__).resolve().parents[1] / "examples" / "quickstart" / "split-stack.models.json"
    monkeypatch.setenv("SPLIT_STACK_MODELS_CONFIG", str(config))
    exit_code = mini_app.main(
        [
            "--prompt",
            "what is caching?",
            "--models",
            "qwen3:4b,qwen3:14b",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"tier": "simple"' in captured.out
    assert '"model": "qwen3:4b"' in captured.out
