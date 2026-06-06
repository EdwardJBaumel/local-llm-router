from split_stack.startup_tips import (
    emit_import_tips,
    model_recommendation_report,
    reset_import_tips_for_tests,
)


def test_model_recommendation_report_returns_lines():
    lines = model_recommendation_report(profile="workstation_12gb")
    assert lines
    assert lines[0].startswith("split-stack:")


def test_emit_import_tips_runs_once(monkeypatch):
    reset_import_tips_for_tests()
    monkeypatch.setenv("SPLIT_STACK_IMPORT_TIPS", "log")
    calls: list[list[str]] = []

    def fake_report(**kwargs):
        lines = ["split-stack: test line"]
        calls.append(lines)
        return lines

    monkeypatch.setattr("split_stack.startup_tips.model_recommendation_report", fake_report)
    emit_import_tips()
    emit_import_tips()
    assert len(calls) == 1
