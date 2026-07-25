"""Strict MCP request and response contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyRequest(StrictModel):
    pass


class ZoneNameRequest(StrictModel):
    zone_name: str = Field(min_length=1, max_length=128)


class DateRangeRequest(StrictModel):
    start: datetime | None = None
    end: datetime | None = None
    aggregation: Literal["raw", "hourly", "daily"] = "raw"
    limit: int = Field(default=200, ge=1, le=500)

    @model_validator(mode="after")
    def validate_range(self) -> "DateRangeRequest":
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be before or equal to end")
        return self


class ZoneTelemetryRequest(DateRangeRequest):
    zone_name: str = Field(min_length=1, max_length=128)


class FacilityTelemetryRequest(DateRangeRequest):
    pass


class ErrorQueryRequest(StrictModel):
    severity: Literal["warning", "severe", "fatal"] | None = None
    classification: str | None = Field(default=None, min_length=1, max_length=128)
    limit: int = Field(default=100, ge=1, le=100)


class BaselineRunRequest(StrictModel):
    verify_reproducibility: bool = False
    force_rebuild: bool = False


class ToolError(StrictModel):
    code: str
    message: str
    recoverable: bool = True


class ToolMetadata(StrictModel):
    requested_at: datetime
    completed_at: datetime
    duration_ms: float
    source: str
    backend: str
    classification: str
    record_count: int = 0
    truncated: bool = False
    audit_id: str


class ToolResponse(StrictModel):
    success: bool
    tool_name: str
    data: Any = None
    error: ToolError | None = None
    metadata: ToolMetadata


class ResourceDocument(StrictModel):
    uri: str
    mime_type: Literal["application/json", "text/markdown"]
    title: str
    content: Any


__all__ = [
    "BaselineRunRequest", "EmptyRequest", "ErrorQueryRequest",
    "FacilityTelemetryRequest", "ResourceDocument", "ToolError", "ToolMetadata",
    "ToolResponse", "ZoneNameRequest", "ZoneTelemetryRequest",
]
