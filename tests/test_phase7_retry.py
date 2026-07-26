from llm.retry import can_retry, retry_prompt


def test_retry_boundaries():
    assert can_retry(0, 2)
    assert can_retry(1, 2)
    assert not can_retry(2, 2)


def test_retry_prompt_contains_required_guardrails():
    prompt = retry_prompt(["unknown zone", "unsupported PMV"], "original task")
    for phrase in ("unknown zone", "unsupported PMV", "original task", "schema", "unsupported facts"):
        assert phrase in prompt
