import json

from local_llm_router.cli import main
from local_llm_router.session import reset_session_for_tests


def setup_function():
    reset_session_for_tests()


def teardown_function():
    reset_session_for_tests()


def test_explain_mode_chat_uses_complex_alt(capsys):
    exit_code = main(
        [
            "explain",
            "--prompt",
            "design the auth module",
            "--hint",
            "design",
            "--mode",
            "chat",
            "--profile",
            "workstation_16gb",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert payload["decision"]["model"] == "qwen3:14b"
    assert payload["decision"]["model_source"] == "complex_alt"


def test_explain_mode_agent_uses_complex_primary(capsys):
    exit_code = main(
        [
            "explain",
            "--prompt",
            "design the auth module",
            "--hint",
            "design",
            "--mode",
            "agent",
            "--profile",
            "workstation_16gb",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert payload["decision"]["model"] == "qwen3.6:35b-a3b"
    assert payload["decision"]["model_source"] == "complex_primary"
