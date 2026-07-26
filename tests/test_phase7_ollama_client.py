import httpx
import pytest

from llm.client import OllamaClient
from llm.errors import AgentError, AgentErrorCode
from llm.settings import LLM_SETTINGS


def _transport(handler):
    return httpx.MockTransport(handler)


def test_unavailable_host():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)
    result = OllamaClient(LLM_SETTINGS, _transport(handler)).discover()
    assert not result.available
    assert result.readiness_issues


def test_model_missing():
    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "1.0"})
        return httpx.Response(200, json={"models": [{"name": "other:latest"}]})
    result = OllamaClient(LLM_SETTINGS, _transport(handler)).discover()
    assert result.available and not result.model_installed


def test_timeout_translated():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)
    with pytest.raises(AgentError) as caught:
        OllamaClient(LLM_SETTINGS, _transport(handler)).chat([], [])
    assert caught.value.code == AgentErrorCode.LLM_TIMEOUT


def test_tool_call_and_metadata_parsing():
    def handler(request):
        body = __import__("json").loads(request.content)
        assert body["think"] is False
        assert body["options"]["num_predict"] == 1_024
        return httpx.Response(200, json={
            "model": "qwen3:4b", "created_at": "now",
            "message": {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "list_zones", "arguments": {}}}
            ]},
            "prompt_eval_count": 10, "eval_count": 3, "eval_duration": 42,
        })
    result = OllamaClient(LLM_SETTINGS, _transport(handler)).chat([], [])
    assert result.tool_calls[0].name == "list_zones"
    assert result.prompt_eval_count == 10


def test_structured_response_and_schema_sent():
    def handler(request):
        body = __import__("json").loads(request.content)
        assert body["stream"] is False
        assert body["think"] is False
        assert body["options"]["temperature"] == 0
        assert body["options"]["num_ctx"] == 4_096
        assert body["options"]["num_predict"] == 192
        assert body["keep_alive"] == "10m"
        assert "tools" not in body
        assert body["format"] == {"type": "object"}
        return httpx.Response(200, json={
            "message": {"role": "assistant", "content": '{"ok":true}'}
        })
    result = OllamaClient(LLM_SETTINGS, _transport(handler)).chat(
        [], [], {"type": "object"}
    )
    assert result.raw_content == '{"ok":true}'


def test_malformed_response():
    def handler(request):
        return httpx.Response(200, json={"message": "bad"})
    with pytest.raises(AgentError) as caught:
        OllamaClient(LLM_SETTINGS, _transport(handler)).chat([], [])
    assert caught.value.code == AgentErrorCode.LLM_INVALID_RESPONSE
