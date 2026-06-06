from split_stack.advice import stack_recommendation


def test_stack_recommendation_defaults():
    advice = stack_recommendation()
    assert advice.cursor_model == "Auto"
    assert advice.warn_cursor_override is False
