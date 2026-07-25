"""Shared execution envelope for all Phase 6 MCP tools."""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable

from pydantic import ValidationError

from mcp_service.audit import sanitize_inputs
from mcp_service.context import MCPApplicationContext
from mcp_service.errors import ErrorCode, MCPToolError
from mcp_service.schemas import ToolError, ToolMetadata, ToolResponse
from mcp_service.serialization import enforce_response_size, to_json_safe


LOGGER = logging.getLogger("ecopilot.mcp")


def _record_count(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if isinstance(data.get("records"), list):
            return len(data["records"])
        if isinstance(data.get("zones"), list):
            return len(data["zones"])
    return 0


def execute_tool(
    context: MCPApplicationContext,
    tool_name: str,
    inputs: Any,
    handler: Callable[[], Any],
    *,
    source: str = "EnergyPlus",
    classification: str = "official_energyplus_baseline",
) -> dict[str, Any]:
    requested = datetime.now(timezone.utc)
    started = time.perf_counter()
    audit_id = context.audit_logger.new_id()
    success = False
    data: Any = None
    public_error: ToolError | None = None
    error_code: str | None = None
    truncated = False
    size = 0
    try:
        data = to_json_safe(handler())
        if isinstance(data, dict):
            truncated = bool(data.get("truncated", False))
        provisional = {"success": True, "tool_name": tool_name, "data": data}
        size = enforce_response_size(provisional, context.settings.max_response_bytes)
        success = True
    except MCPToolError as exc:
        error_code = exc.code.value
        public_error = ToolError(
            code=error_code, message=exc.public_message, recoverable=exc.recoverable
        )
    except ValidationError:
        error_code = ErrorCode.INVALID_REQUEST.value
        public_error = ToolError(
            code=error_code, message="Request validation failed.", recoverable=True
        )
    except Exception:
        LOGGER.exception("Unhandled MCP tool failure: %s", tool_name)
        error_code = ErrorCode.INTERNAL_ERROR.value
        public_error = ToolError(
            code=error_code,
            message="The tool failed internally. Check server diagnostics using get_system_status.",
            recoverable=True,
        )
    completed = datetime.now(timezone.utc)
    duration_ms = (time.perf_counter() - started) * 1000
    response = ToolResponse(
        success=success,
        tool_name=tool_name,
        data=data if success else None,
        error=public_error,
        metadata=ToolMetadata(
            requested_at=requested,
            completed_at=completed,
            duration_ms=duration_ms,
            source=source,
            backend="energyplus",
            classification=classification,
            record_count=_record_count(data),
            truncated=truncated,
            audit_id=audit_id,
        ),
    )
    response_dict = to_json_safe(response)
    if success:
        size = enforce_response_size(response_dict, context.settings.max_response_bytes)
    context.audit_logger.write({
        "audit_id": audit_id,
        "tool_name": tool_name,
        "sanitized_inputs": sanitize_inputs(inputs),
        "success": success,
        "duration_ms": duration_ms,
        "result_record_count": _record_count(data),
        "result_size_bytes": size,
        "error_code": error_code,
        "source": source,
        "classification": classification,
    })
    return response_dict


__all__ = ["execute_tool"]
