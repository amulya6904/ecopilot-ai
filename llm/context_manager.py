"""Compact, role-safe Phase 7 conversation context."""

import json
from typing import Any

from llm.errors import AgentError, AgentErrorCode
from llm.settings import LLMSettings


class AgentContextManager:
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.messages: list[dict[str, Any]] = []

    def append(self, message: dict[str, Any]) -> None:
        if message.get("role") == "tool" and "tool_name" not in message:
            raise AgentError(AgentErrorCode.INTERNAL_ERROR, "Tool messages require a source tool name.")
        candidate = [*self.messages, message]
        size = len(json.dumps(candidate, sort_keys=True, default=str))
        if size > self.settings.max_context_characters:
            raise AgentError(
                AgentErrorCode.CONTEXT_TOO_LARGE,
                f"Agent context would exceed {self.settings.max_context_characters} characters.",
            )
        self.messages.append(message)

    @property
    def character_count(self) -> int:
        return len(json.dumps(self.messages, sort_keys=True, default=str))

    def append_tool_result(self, tool: str, content: str) -> None:
        if "raw_log_excerpt" in content:
            content = content.replace("raw_log_excerpt", "excluded_raw_log")
        self.append({"role": "tool", "tool_name": tool, "content": content})


__all__ = ["AgentContextManager"]
