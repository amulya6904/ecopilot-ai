"""Date filtering, aggregation, and stable record limiting."""

from datetime import datetime
from typing import Any

import pandas as pd

from mcp_service.errors import ErrorCode, MCPToolError


def bounded_frame(
    frame: pd.DataFrame,
    *,
    start: datetime | None,
    end: datetime | None,
    aggregation: str,
    limit: int,
    maximum: int,
    group_columns: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if aggregation not in {"raw", "hourly", "daily"}:
        raise MCPToolError(ErrorCode.INVALID_AGGREGATION, "Aggregation must be raw, hourly, or daily.")
    if limit < 1 or limit > maximum:
        raise MCPToolError(ErrorCode.LIMIT_EXCEEDED, f"limit must be between 1 and {maximum}.")
    result = frame.copy()
    if "timestamp" not in result:
        raise MCPToolError(ErrorCode.BASELINE_NOT_AVAILABLE, "Telemetry has no timestamp column.")
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
    if start is not None:
        result = result[result["timestamp"] >= pd.Timestamp(start)]
    if end is not None:
        result = result[result["timestamp"] <= pd.Timestamp(end)]
    if aggregation != "raw" and not result.empty:
        frequency = "h" if aggregation == "hourly" else "D"
        keys = [*group_columns, pd.Grouper(key="timestamp", freq=frequency)]
        numeric = list(result.select_dtypes(include="number").columns)
        result = result.groupby(keys, dropna=False, as_index=False)[numeric].mean()
    result = result.sort_values("timestamp", kind="stable")
    total = len(result)
    truncated = total > limit
    result = result.head(limit).reset_index(drop=True)
    return result, {
        "truncated": truncated,
        "returned_records": len(result),
        "total_matching_records": total,
        "recommended_narrower_query": (
            "Use a smaller date range or a coarser aggregation." if truncated else None
        ),
    }


__all__ = ["bounded_frame"]
