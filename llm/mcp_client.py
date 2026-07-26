"""Official-SDK stdio bridge from Phase 7 to the Phase 6 server."""

from contextlib import asynccontextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, AsyncIterator, Callable

from jsonschema import ValidationError as JSONSchemaValidationError, validate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from llm.errors import AgentError, AgentErrorCode
from llm.settings import LLMSettings


MODEL_TOOL_ALLOWLIST = (
    "get_system_status", "get_energyplus_readiness",
    "get_official_baseline_summary", "get_available_outputs", "list_zones",
    "get_zone_summary", "get_zone_telemetry", "get_facility_summary",
    "get_facility_telemetry", "get_comfort_summary",
    "get_thermostat_adherence", "get_runtime_errors",
)


def _strict_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Reject model-invented top-level arguments not declared by MCP."""
    strict = deepcopy(schema)
    if strict.get("type") == "object":
        strict["additionalProperties"] = False
    return strict


def _structured(result: Any) -> dict[str, Any]:
    if isinstance(result.structuredContent, dict):
        return result.structuredContent
    if result.content and hasattr(result.content[0], "text"):
        value = json.loads(result.content[0].text)
        if isinstance(value, dict):
            return value
    raise AgentError(AgentErrorCode.TOOL_CALL_FAILED, "MCP tool returned no structured object.")


def _sanitize_tool_content(text: str) -> str:
    lowered = text.casefold()
    suspicious = ("ignore previous", "system instruction", "run shell", "execute command", "powershell")
    return "[untrusted instruction removed]" if any(item in lowered for item in suspicious) else text


_MODEL_DATA_FIELDS: dict[str, tuple[str, ...]] = {
    "get_system_status": (
        "project_status", "energyplus", "official_baseline", "phase6_mcp",
    ),
    "get_official_baseline_summary": (
        "run_id", "source", "classification", "official_result",
        "baseline_result", "total_facility_electricity_kwh",
        "total_hvac_electricity_kwh", "total_cooling_electricity_kwh",
        "average_facility_demand_kw", "peak_facility_demand_kw",
        "peak_demand_timestamp", "temperature_compliance_percent",
        "pmv_available", "pmv_unavailable_reason",
        "thermostat_adherence_percent",
    ),
    "get_facility_summary": (
        "total_facility_electricity_kwh", "average_facility_demand_kw",
        "peak_facility_demand_kw", "peak_demand_timestamp",
    ),
    "get_comfort_summary": (
        "comfort_range_c", "excluded_roles", "occupancy_source",
        "temperature_compliance_percent", "temperature_violation_count",
        "minimum_occupied_temperature_c", "maximum_occupied_temperature_c",
        "pmv_available", "pmv_unavailable_reason", "pmv_compliance_percent",
    ),
    "get_thermostat_adherence": (
        "frozen_policy", "adherence_percent", "mismatch_count",
    ),
}


def _compact_model_result(name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Keep full MCP data for validation/audit and send a compact evidence view."""
    data = result.get("data")
    if isinstance(data, dict) and name in _MODEL_DATA_FIELDS:
        fields = _MODEL_DATA_FIELDS[name]
        data = {field: data.get(field) for field in fields if field in data}
    metadata = result.get("metadata")
    compact_metadata: dict[str, Any] = {}
    if isinstance(metadata, dict):
        for field in (
            "source", "backend", "classification", "record_count", "truncated",
        ):
            if field in metadata:
                compact_metadata[field] = metadata[field]
    return {
        "success": result.get("success"),
        "tool_name": name,
        "data": data,
        "metadata": compact_metadata,
    }


def _nested_agent_error(exc: BaseException) -> AgentError | None:
    if isinstance(exc, AgentError):
        return exc
    if isinstance(exc, BaseExceptionGroup):
        for nested in exc.exceptions:
            found = _nested_agent_error(nested)
            if found is not None:
                return found
    return None


class MCPBridge:
    def __init__(
        self,
        settings: LLMSettings,
        session_context_factory: Callable[[], Any] | None = None,
    ):
        self.settings = settings
        self._factory = session_context_factory
        self.session: ClientSession | Any | None = None
        self.tools_by_name: dict[str, Any] = {}
        self.tool_history: list[dict[str, Any]] = []

    @asynccontextmanager
    async def connect(self) -> AsyncIterator["MCPBridge"]:
        if self._factory is not None:
            async with self._factory() as session:
                self.session = session
                await self._initialize()
                yield self
                self.session = None
            return
        if sys.platform == "win32":
            import mcp.os.win32.utilities as windows_utilities
            windows_utilities._create_job_object = lambda: None
        repository = Path(self.settings.repository_root).resolve()
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "scripts.run_phase6_mcp_server"],
            cwd=repository,
            env=dict(os.environ),
        )
        try:
            async with stdio_client(parameters) as streams:
                async with ClientSession(*streams) as session:
                    self.session = session
                    await self._initialize()
                    yield self
                    self.session = None
        except AgentError:
            raise
        except Exception as exc:
            nested = _nested_agent_error(exc)
            if nested is not None:
                raise nested
            raise AgentError(AgentErrorCode.MCP_UNAVAILABLE, "Could not initialize the local Phase 6 MCP server.") from exc

    async def _initialize(self) -> None:
        if self.session is None:
            raise AgentError(AgentErrorCode.MCP_UNAVAILABLE, "MCP session is unavailable.")
        await self.session.initialize()
        listed = await self.session.list_tools()
        discovered = {tool.name: tool for tool in listed.tools}
        self.tools_by_name = {
            name: discovered[name] for name in MODEL_TOOL_ALLOWLIST if name in discovered
        }
        missing = set(MODEL_TOOL_ALLOWLIST) - set(self.tools_by_name)
        if missing:
            raise AgentError(AgentErrorCode.MCP_UNAVAILABLE, f"Required read-only MCP tools are missing: {sorted(missing)}")

    def ollama_tools(self) -> list[dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "Read verified EnergyPlus baseline data.",
                "parameters": _strict_input_schema(tool.inputSchema),
            },
        } for tool in self.tools_by_name.values()]

    async def call_tool(self, name: str, arguments: dict[str, Any], round_number: int) -> dict[str, Any]:
        if name not in self.tools_by_name:
            raise AgentError(AgentErrorCode.TOOL_NOT_ALLOWED, f"Model-selected tool is not allowlisted: {name}.")
        try:
            validate(
                instance=arguments,
                schema=_strict_input_schema(self.tools_by_name[name].inputSchema),
            )
        except JSONSchemaValidationError as exc:
            raise AgentError(AgentErrorCode.TOOL_ARGUMENT_INVALID, f"Invalid arguments for {name}: {exc.message}") from exc
        started = time.perf_counter()
        try:
            result = _structured(await self.session.call_tool(name, arguments))
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError(AgentErrorCode.TOOL_CALL_FAILED, f"MCP call failed: {name}.") from exc
        duration_ms = (time.perf_counter() - started) * 1000
        if result.get("success") is not True:
            error = result.get("error") or {}
            raise AgentError(AgentErrorCode.TOOL_CALL_FAILED, f"{name} failed: {error.get('code', 'unknown error')}.")
        encoded = json.dumps(
            _compact_model_result(name, result),
            sort_keys=True,
            allow_nan=False,
        )
        truncated = len(encoded) > self.settings.max_tool_result_characters
        bounded = encoded[:self.settings.max_tool_result_characters]
        bounded = _sanitize_tool_content(bounded)
        event = {
            "round": round_number, "tool": name, "arguments": arguments,
            "duration_ms": duration_ms, "success": True, "response": result,
            "model_content": bounded, "truncated": truncated,
        }
        self.tool_history.append(event)
        return event


__all__ = ["MCPBridge", "MODEL_TOOL_ALLOWLIST"]
