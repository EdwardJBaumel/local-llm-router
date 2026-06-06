import json

import pytest

from split_stack.cli import main
from split_stack.compare import (
    DEFAULT_STEPS,
    CompareRunError,
    format_compare_text,
    largest_model,
    run_compare,
)
from split_stack.ollama_errors import format_ollama_error


def test_largest_model_picks_heaviest():
    assert largest_model(["gemma4:e4b", "qwen3:8b", "qwen3:14b"]) == "qwen3:14b"


def test_run_compare_dry_spreads_models():
    report = run_compare(model_names=["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    assert len(report.rows) == len(DEFAULT_STEPS)
    assert report.summary.baseline_model == "qwen3:14b"
    assert report.summary.routed_models_used == 3
    assert report.summary.baseline_models_used == 1
    assert report.summary.steps_avoided_largest == 3
    assert report.summary.routed_total_latency_ms is None

    quick = next(row for row in report.rows if row.step == "quick_lookup")
    assert quick.routed_model == "gemma4:e4b"
    assert quick.baseline_model == "qwen3:14b"

    design = next(row for row in report.rows if row.step == "design")
    assert design.routed_model == "qwen3:14b"


def test_format_compare_text_includes_summary():
    report = run_compare(model_names=["gemma4:e4b", "qwen3:8b", "qwen3:14b"])
    text = format_compare_text(report)
    assert "Compare: split-stack vs always-largest (qwen3:14b)" in text
    assert "quick_lookup" in text
    assert "3/5 steps avoided largest" in text


def test_stack_compare_cli(capsys):
    exit_code = main(["compare"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "split-stack vs always-largest" in output
    assert "3/5 steps avoided largest" in output
    assert "gemma4:e4b" in output or "qwen3:8b" in output


def test_stack_compare_json(capsys):
    exit_code = main(["compare", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert len(payload["rows"]) == 5
    assert payload["summary"]["steps_avoided_largest"] == 3


def test_format_ollama_error_404():
    requests = pytest.importorskip("requests")
    response = requests.Response()
    response.status_code = 404
    err = requests.HTTPError(response=response)
    message = format_ollama_error(err, model="qwen3:14b")
    assert "qwen3:14b" in message
    assert "ollama pull qwen3:14b" in message


def test_format_ollama_error_connection():
    requests = pytest.importorskip("requests")
    err = requests.ConnectionError("refused")
    message = format_ollama_error(err, model="qwen3:8b", base_url="http://127.0.0.1:11434")
    assert "not reachable" in message
    assert "127.0.0.1:11434" in message


def test_compare_run_error_message():
    err = CompareRunError("quick_lookup", "qwen3:4b", "Model 'qwen3:4b' not found.")
    assert "quick_lookup" in str(err)
    assert "qwen3:4b" in str(err)


def test_stack_compare_live_missing_model(capsys, monkeypatch):
    def fake_generate(*args, **kwargs):
        raise RuntimeError("Model 'qwen3:14b' not found. Run: ollama pull qwen3:14b")

    monkeypatch.setattr("split_stack.ollama_generate.generate_text", fake_generate)
    exit_code = main(["compare", "--live"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ollama pull" in captured.err.lower() or "ollama pull" in captured.err
