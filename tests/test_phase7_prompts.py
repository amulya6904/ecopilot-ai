from llm.prompts import DEFAULT_AGENT_TASK, PROMPT_VERSION, SYSTEM_PROMPT, user_prompt


def test_prompt_is_versioned_and_advisory():
    assert PROMPT_VERSION
    for phrase in ("advisory", "MCP", "PMV", "non-plenum", "not applied"):
        assert phrase.casefold() in SYSTEM_PROMPT.casefold()


def test_user_prompt_contains_task_without_schema():
    prompt = user_prompt(DEFAULT_AGENT_TASK)
    assert DEFAULT_AGENT_TASK in prompt
    assert "Required final JSON schema" not in prompt


def test_initial_prompt_requires_native_evidence_tool_calls():
    prompt = user_prompt(DEFAULT_AGENT_TASK, include_schema=False)
    assert "only native tool calls" in prompt
    assert "get_official_baseline_summary" in prompt
    assert "get_thermostat_adherence" in prompt
    assert "Required final JSON schema" not in prompt
