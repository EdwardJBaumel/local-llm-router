import json
from unittest.mock import patch

from local_llm_router.cli import main


def test_stack_route_json_with_models(capsys):
    exit_code = main(
        [
            "route",
            "--prompt",
            "what is caching?",
            "--json",
            "--models",
            "qwen3:4b,qwen3:14b",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["tier"] == "simple"
    assert payload["model"] == "qwen3:4b"


def test_stack_route_json_complex_prompt(capsys):
    exit_code = main(
        [
            "route",
            "--prompt",
            "design a distributed retry strategy",
            "--json",
            "--models",
            "qwen3:4b,qwen3:8b,qwen3:14b",
        ]
    )
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert payload["tier"] == "complex"
    assert payload["model"] == "qwen3:14b"


@patch("local_llm_router.ollama_generate.generate_text", return_value="Caching stores copies of data.")
@patch(
    "local_llm_router.ollama_generate._resolve_model_names",
    return_value=(["qwen3:4b", "qwen3:14b"], None),
)
def test_stack_ask_json(_mock_resolve, _mock_generate, capsys):
    exit_code = main(["ask", "--prompt", "what is caching?", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["tier"] == "simple"
    assert payload["model"] == "qwen3:4b"
    assert "Caching" in payload["text"]


def test_stack_ask_json_discovery_error(capsys):
    with patch(
        "local_llm_router.ollama_generate._resolve_model_names",
        return_value=([], None),
    ):
        exit_code = main(["ask", "--prompt", "what is caching?", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 1
    assert payload["ready"] is False
    assert "No models available" in payload["error"]


def test_stack_profiles_json(capsys):
    exit_code = main(["profiles", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    names = {item["name"] for item in payload["profiles"]}
    assert "workstation_12gb" in names
    assert "workstation_32gb" in names
    assert "datacenter" in names
