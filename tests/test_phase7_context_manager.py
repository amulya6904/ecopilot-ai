from dataclasses import replace

import pytest

from llm.context_manager import AgentContextManager
from llm.errors import AgentError, AgentErrorCode
from llm.settings import LLM_SETTINGS


def test_tool_content_stays_tool_role_and_raw_log_is_excluded():
    context = AgentContextManager(LLM_SETTINGS)
    context.append_tool_result("get_runtime_errors", '{"raw_log_excerpt":"secret"}')
    assert context.messages[0]["role"] == "tool"
    assert context.messages[0]["tool_name"] == "get_runtime_errors"
    assert "raw_log_excerpt" not in context.messages[0]["content"]


def test_context_limit_enforced():
    settings = replace(LLM_SETTINGS, max_context_characters=100)
    context = AgentContextManager(settings)
    with pytest.raises(AgentError) as caught:
        context.append({"role": "user", "content": "x" * 200})
    assert caught.value.code == AgentErrorCode.CONTEXT_TOO_LARGE


def test_tool_message_cannot_be_promoted_or_unattributed():
    context = AgentContextManager(LLM_SETTINGS)
    with pytest.raises(AgentError):
        context.append({"role": "tool", "content": "untrusted"})
