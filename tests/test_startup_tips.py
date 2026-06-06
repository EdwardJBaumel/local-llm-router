from local_llm_router.startup_tips import (
    emit_import_tips,
    model_recommendation_report,
    reset_import_tips_for_tests,
)


def test_model_recommendation_report_returns_lines():
    lines = model_recommendation_report(profile="workstation_12gb")
    assert lines
    assert lines[0].startswith("local-llm-router:")


def test_emit_import_tips_runs_once(monkeypatch):
    reset_import_tips_for_tests()
    monkeypatch.setenv("local_llm_router_IMPORT_TIPS", "log")
    calls: list[list[str]] = []

    def fake_report(**kwargs):
        lines = ["local-llm-router: test line"]
        calls.append(lines)
        return lines

    monkeypatch.setattr("local_llm_router.startup_tips.model_recommendation_report", fake_report)
    emit_import_tips()
    emit_import_tips()
    assert len(calls) == 1
