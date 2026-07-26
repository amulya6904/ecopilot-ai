from dataclasses import replace

import pytest

from llm.settings import LLM_SETTINGS, LLMSettings


def test_valid_defaults():
    assert LLM_SETTINGS.model == "qwen3:4b"
    assert LLM_SETTINGS.temperature == 0.1
    assert LLM_SETTINGS.think is False
    assert LLM_SETTINGS.request_timeout_seconds == 180
    assert LLM_SETTINGS.final_request_timeout_seconds == 180
    assert LLM_SETTINGS.agent_run_timeout_seconds == 360
    assert LLM_SETTINGS.max_tool_rounds == 4
    assert LLM_SETTINGS.max_retries == 1
    assert LLM_SETTINGS.num_predict == 192
    assert LLM_SETTINGS.num_ctx == 4_096
    assert LLM_SETTINGS.advisory_only is True
    assert LLM_SETTINGS.control_execution_enabled is False


@pytest.mark.parametrize("field,value", [
    ("temperature", 1.1), ("request_timeout_seconds", 0),
    ("final_request_timeout_seconds", 0),
    ("agent_run_timeout_seconds", 0), ("max_tool_rounds", 0),
    ("num_predict", 0), ("num_ctx", 0),
])
def test_invalid_numeric_settings(field, value):
    with pytest.raises(ValueError):
        replace(LLM_SETTINGS, **{field: value})


def test_control_execution_cannot_be_enabled():
    with pytest.raises(ValueError):
        replace(LLM_SETTINGS, control_execution_enabled=True)


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("ECOPILOT_LLM_MODEL", "local:test")
    monkeypatch.setenv("ECOPILOT_AGENT_MAX_RETRIES", "3")
    monkeypatch.setenv("ECOPILOT_LLM_THINK", "true")
    settings = LLMSettings()
    assert settings.model == "local:test"
    assert settings.max_retries == 3
    assert settings.think is True
