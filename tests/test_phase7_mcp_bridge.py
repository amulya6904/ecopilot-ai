import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from llm.errors import AgentError, AgentErrorCode
from llm.mcp_client import MCPBridge, MODEL_TOOL_ALLOWLIST
from llm.settings import LLM_SETTINGS


class FakeSession:
    def __init__(self):
        self.initialized = False
        self.closed = False
        self.tools = [
            SimpleNamespace(
                name=name, description=name,
                inputSchema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                    "additionalProperties": False,
                },
            ) for name in MODEL_TOOL_ALLOWLIST
        ] + [SimpleNamespace(
            name="run_official_baseline", description="excluded",
            inputSchema={"type": "object"},
        )]

    async def initialize(self):
        self.initialized = True

    async def list_tools(self):
        return SimpleNamespace(tools=self.tools)

    async def call_tool(self, name, arguments):
        return SimpleNamespace(
            structuredContent={
                "success": True, "data": {"payload": "x" * 500},
                "metadata": {"classification": "official_energyplus_baseline"},
            },
            content=[],
        )


def factory(session):
    @asynccontextmanager
    async def context():
        try:
            yield session
        finally:
            session.closed = True
    return context


def test_initialize_discovery_allowlist_and_shutdown():
    async def scenario():
        session = FakeSession()
        bridge = MCPBridge(LLM_SETTINGS, factory(session))
        async with bridge.connect():
            assert session.initialized
            assert set(bridge.tools_by_name) == set(MODEL_TOOL_ALLOWLIST)
            assert "run_official_baseline" not in bridge.tools_by_name
        assert session.closed
    asyncio.run(scenario())


def test_undeclared_arguments_rejected_even_when_mcp_schema_is_loose():
    async def scenario():
        session = FakeSession()
        session.tools[0].inputSchema = {"type": "object", "properties": {}}
        bridge = MCPBridge(LLM_SETTINGS, factory(session))
        async with bridge.connect():
            with pytest.raises(AgentError) as caught:
                await bridge.call_tool(MODEL_TOOL_ALLOWLIST[0], {"invented": True}, 1)
        assert caught.value.code == AgentErrorCode.TOOL_ARGUMENT_INVALID
    asyncio.run(scenario())


def test_unknown_tool_rejected():
    async def scenario():
        session = FakeSession()
        bridge = MCPBridge(LLM_SETTINGS, factory(session))
        async with bridge.connect():
            with pytest.raises(AgentError) as caught:
                await bridge.call_tool("run_official_baseline", {}, 1)
        assert caught.value.code == AgentErrorCode.TOOL_NOT_ALLOWED
    asyncio.run(scenario())


def test_invalid_arguments_rejected():
    async def scenario():
        session = FakeSession()
        bridge = MCPBridge(LLM_SETTINGS, factory(session))
        async with bridge.connect():
            with pytest.raises(AgentError) as caught:
                await bridge.call_tool("list_zones", {"limit": "bad"}, 1)
        assert caught.value.code == AgentErrorCode.TOOL_ARGUMENT_INVALID
    asyncio.run(scenario())


def test_tool_response_is_bounded():
    async def scenario():
        settings = replace(LLM_SETTINGS, max_tool_result_characters=100)
        session = FakeSession()
        bridge = MCPBridge(settings, factory(session))
        async with bridge.connect():
            event = await bridge.call_tool("list_zones", {}, 1)
        assert event["truncated"] is True
        assert len(event["model_content"]) <= 100
    asyncio.run(scenario())
