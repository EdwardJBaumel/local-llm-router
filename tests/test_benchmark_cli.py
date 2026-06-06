import json

from split_stack.cli import main


def test_stack_benchmark_markdown(capsys):
    exit_code = main(["benchmark", "--markdown", "--models", "qwen3:4b,qwen3:8b,qwen3:14b"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "| b01 |" in output
    assert "tier_counts:" in output


def test_stack_benchmark_json(capsys):
    exit_code = main(["benchmark", "--json", "--models", "qwen3:4b,qwen3:14b"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert len(payload["rows"]) == 10
