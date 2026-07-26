"""Bounded EnergyPlus runtime diagnostics."""

from typing import Any

from mcp_service.context import MCPApplicationContext
from mcp_service.errors import ErrorCode, MCPToolError
from mcp_service.tools import execute_tool


def get_runtime_errors(
    context: MCPApplicationContext,
    *,
    severity: str | None = None,
    classification: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    effective_limit = limit or context.settings.max_error_records
    inputs = {"severity": severity, "classification": classification, "limit": effective_limit}
    def handler() -> Any:
        if severity is not None and severity not in {"warning", "severe", "fatal"}:
            raise MCPToolError(ErrorCode.INVALID_REQUEST, "severity must be warning, severe, or fatal.")
        if effective_limit < 1 or effective_limit > context.settings.max_error_records:
            raise MCPToolError(ErrorCode.LIMIT_EXCEEDED, f"limit must be between 1 and {context.settings.max_error_records}.")
        errors = context.load_json("errors.json")
        records = errors.get("records", [])
        known_classifications = {str(item.get("classification")) for item in records}
        if classification is not None and classification not in known_classifications:
            raise MCPToolError(ErrorCode.INVALID_REQUEST, "Unknown diagnostic classification.")
        filtered = [
            item for item in records
            if (severity is None or item.get("severity") == severity)
            and (classification is None or item.get("classification") == classification)
        ]
        compact = []
        for item in filtered[:effective_limit]:
            compact.append({
                "severity": item.get("severity"),
                "classification": item.get("classification"),
                "message": str(item.get("message", ""))[:context.settings.max_raw_log_characters],
                "recoverable": item.get("recoverable"),
                "run_id": errors.get("run_id"),
            })
        return {
            "warning_count": errors.get("warning_count", 0),
            "severe_count": errors.get("severe_count", 0),
            "fatal_count": errors.get("fatal_count", 0),
            "records": compact,
            "truncated": len(filtered) > len(compact),
            "returned_records": len(compact),
            "total_matching_records": len(filtered),
        }
    return execute_tool(context, "get_runtime_errors", inputs, handler)


__all__ = ["get_runtime_errors"]
