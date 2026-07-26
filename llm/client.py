"""Lightweight Ollama REST client using the existing httpx dependency."""

from typing import Any
import httpx

from llm.errors import AgentError, AgentErrorCode
from llm.schemas import LLMClientResult, OllamaAvailability, ToolCall
from llm.settings import LLMSettings


class OllamaClient:
    def __init__(self, settings: LLMSettings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._transport = transport

    def discover(self) -> OllamaAvailability:
        issues: list[str] = []
        version = None
        names: list[str] = []
        try:
            with httpx.Client(base_url=self.settings.host, timeout=min(10, self.settings.request_timeout_seconds), transport=self._transport) as client:
                version_response = client.get("/api/version")
                version_response.raise_for_status()
                version = version_response.json().get("version")
                tags_response = client.get("/api/tags")
                tags_response.raise_for_status()
                models = tags_response.json().get("models")
                if not isinstance(models, list):
                    raise ValueError("models must be a list")
                names = sorted({
                    str(item.get("model") or item.get("name"))
                    for item in models if isinstance(item, dict) and (item.get("model") or item.get("name"))
                })
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            issues.append(f"Ollama did not return a valid local API response: {type(exc).__name__}.")
        installed = self.settings.model in names
        if names and not installed:
            issues.append(f"Configured model {self.settings.model!r} is not installed.")
        available = version is not None
        return OllamaAvailability(
            available=available, host=self.settings.host, version=version,
            configured_model=self.settings.model, model_installed=installed,
            installed_models=names, reason=issues[0] if issues else None,
            readiness_issues=issues,
        )

    def _chat_payload(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        format_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        final_request = format_schema is not None
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "stream": False,
            "think": self.settings.think,
            "keep_alive": "10m",
            "options": {
                "temperature": 0 if final_request else self.settings.temperature,
                "num_ctx": self.settings.num_ctx if final_request else 8_192,
                "num_predict": self.settings.num_predict if final_request else 1_024,
            },
        }
        if tools:
            payload["tools"] = tools
        if format_schema is not None:
            payload["format"] = format_schema
        return payload

    def _request_timeout(self, format_schema: dict[str, Any] | None) -> int:
        return (
            self.settings.final_request_timeout_seconds
            if format_schema is not None
            else self.settings.request_timeout_seconds
        )

    def _parse_chat_response(self, body: dict[str, Any]) -> LLMClientResult:
        message = body.get("message")
        if not isinstance(message, dict):
            raise AgentError(AgentErrorCode.LLM_INVALID_RESPONSE, "Ollama response has no valid message.")
        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            function = item.get("function", {}) if isinstance(item, dict) else {}
            name, arguments = function.get("name"), function.get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise AgentError(AgentErrorCode.LLM_INVALID_RESPONSE, "Ollama returned a malformed tool call.")
            calls.append(ToolCall(name=name, arguments=arguments))
        return LLMClientResult(
            model=str(body.get("model") or self.settings.model),
            created_at=body.get("created_at"), message=message, tool_calls=calls,
            raw_content=str(message.get("content") or ""),
            prompt_eval_duration_ns=body.get("prompt_eval_duration"),
            generation_duration_ns=body.get("eval_duration"),
            prompt_eval_count=body.get("prompt_eval_count"),
            eval_count=body.get("eval_count"),
            total_duration_ns=body.get("total_duration"),
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        format_schema: dict[str, Any] | None = None,
    ) -> LLMClientResult:
        payload = self._chat_payload(messages, tools, format_schema)
        try:
            with httpx.Client(
                base_url=self.settings.host,
                timeout=self._request_timeout(format_schema),
                transport=self._transport,
            ) as client:
                response = client.post("/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise AgentError(AgentErrorCode.LLM_TIMEOUT, "Ollama chat request timed out.") from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise AgentError(AgentErrorCode.OLLAMA_UNAVAILABLE, "Ollama chat request failed.") from exc
        return self._parse_chat_response(body)

    async def chat_async(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        format_schema: dict[str, Any] | None = None,
    ) -> LLMClientResult:
        """Send a cancellable request so the overall agent timeout is effective."""
        payload = self._chat_payload(messages, tools, format_schema)
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.host,
                timeout=self._request_timeout(format_schema),
            ) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise AgentError(AgentErrorCode.LLM_TIMEOUT, "Ollama chat request timed out.") from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise AgentError(AgentErrorCode.OLLAMA_UNAVAILABLE, "Ollama chat request failed.") from exc
        return self._parse_chat_response(body)


__all__ = ["OllamaClient"]
