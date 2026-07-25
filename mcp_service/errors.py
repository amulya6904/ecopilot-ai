"""Stable public errors for Phase 6."""

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_ZONE = "INVALID_ZONE"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVALID_AGGREGATION = "INVALID_AGGREGATION"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    ENERGYPLUS_UNAVAILABLE = "ENERGYPLUS_UNAVAILABLE"
    BASELINE_NOT_AVAILABLE = "BASELINE_NOT_AVAILABLE"
    RUN_ALREADY_IN_PROGRESS = "RUN_ALREADY_IN_PROGRESS"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class MCPToolError(Exception):
    def __init__(self, code: ErrorCode, message: str, recoverable: bool = True):
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.recoverable = recoverable


__all__ = ["ErrorCode", "MCPToolError"]
