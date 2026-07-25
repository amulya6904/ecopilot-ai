"""Deterministic bounded conversion of EcoPilot values to strict JSON."""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from mcp_service.errors import ErrorCode, MCPToolError


def to_json_safe(value: Any, *, max_depth: int = 20, _depth: int = 0) -> Any:
    if _depth > max_depth:
        raise MCPToolError(ErrorCode.RESPONSE_TOO_LARGE, "Maximum serialization depth exceeded.")
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        raise MCPToolError(ErrorCode.INTERNAL_ERROR, "Binary values are not MCP serializable.")
    if isinstance(value, pd.DataFrame):
        return to_json_safe(value.to_dict(orient="records"), max_depth=max_depth, _depth=_depth + 1)
    if value is pd.NaT:
        return None
    if not isinstance(value, (list, tuple, dict, str, set)):
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and bool(missing):
            return None
    if isinstance(value, BaseModel):
        value = value.model_dump()
    elif is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {
            str(key): to_json_safe(item, max_depth=max_depth, _depth=_depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [
            to_json_safe(item, max_depth=max_depth, _depth=_depth + 1)
            for item in value
        ]
    raise MCPToolError(ErrorCode.INTERNAL_ERROR, f"Unsupported response type: {type(value).__name__}.")


def json_bytes(value: Any) -> bytes:
    return json.dumps(to_json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def enforce_response_size(value: Any, maximum_bytes: int) -> int:
    size = len(json_bytes(value))
    if size > maximum_bytes:
        raise MCPToolError(
            ErrorCode.RESPONSE_TOO_LARGE,
            f"Response is {size} bytes; maximum is {maximum_bytes}. Use a narrower query.",
        )
    return size


__all__ = ["enforce_response_size", "json_bytes", "to_json_safe"]
