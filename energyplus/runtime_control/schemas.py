"""Strict Phase 8 telemetry, action, validation, and event schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RuntimeTelemetrySnapshot(StrictRuntimeModel):
    simulation_timestamp: datetime
    environment_name: str
    warmup_flag: bool
    zone_name: str
    zone_temperature_c: float
    outdoor_temperature_c: float | None
    current_cooling_setpoint_c: float
    current_heating_setpoint_c: float | None
    occupancy: float | None
    facility_demand_kw: float | None
    facility_energy_j: float | None
    handles_ready: bool
    source: Literal["EnergyPlusRuntime"] = "EnergyPlusRuntime"
    relative_humidity_percent: float | None = None
    pmv: float | None = None
    ppd_percent: float | None = None


class ExecutableActionCandidate(StrictRuntimeModel):
    action_id: str = Field(min_length=1)
    source_proposal_id: str | None
    source_type: Literal["manual", "mock_agent", "phase7_llm", "fallback"]
    zone_name: str = Field(min_length=1)
    actuator_identifier: str = Field(min_length=1)
    current_value_c: float
    requested_value_c: float
    requested_delta_c: float
    effective_from: datetime
    effective_until: datetime
    evidence_references: list[str]
    created_at: datetime
    expires_at: datetime
    phase7_validated: bool | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    run_id: str | None = None
    objective: Literal[
        "reduce_energy",
        "reduce_peak_demand",
        "maintain_comfort",
    ] = "maintain_comfort"
    control_type: Literal["cooling_setpoint"] = "cooling_setpoint"
    reason: str = ""

    @model_validator(mode="after")
    def validate_period_and_delta(self) -> "ExecutableActionCandidate":
        if self.effective_until <= self.effective_from:
            raise ValueError("Action effective window must be ordered.")
        if self.expires_at < self.created_at:
            raise ValueError("Action expiration cannot precede creation.")
        if abs(
            self.requested_value_c
            - self.current_value_c
            - self.requested_delta_c
        ) > 1e-6:
            raise ValueError("Requested delta must equal requested minus current.")
        return self


class ActionValidationResult(StrictRuntimeModel):
    validation_id: str
    valid: bool
    approved: bool
    outcome: Literal[
        "approved",
        "approved_with_clamp",
        "hold",
        "rejected",
        "fallback",
    ]
    requested_value_c: float
    approved_value_c: float | None
    errors: list[str]
    warnings: list[str]
    risk_level: Literal["low", "medium", "high"]
    validator_version: str
    fallback_required: bool
    validation_latency_ms: float = Field(ge=0)


class AppliedControlEvent(StrictRuntimeModel):
    action_id: str
    simulation_timestamp: datetime
    actuator_handle: int
    requested_value: float
    approved_value: float
    applied_value: float
    application_success: bool
    observed_setpoint_after_application: float | None
    reset_performed: bool
    source_type: Literal["manual", "mock_agent", "phase7_llm", "fallback"]
    validation_id: str
    verified: bool = False


class FallbackEvent(StrictRuntimeModel):
    fallback_id: str
    reason_code: Literal[
        "NO_ACTION_READY",
        "ACTION_STALE",
        "VALIDATION_REJECTED",
        "AGENT_TIMEOUT",
        "AGENT_FAILURE",
        "INVALID_ACTUATOR",
        "MISSING_TELEMETRY",
        "CALLBACK_FAILURE",
        "COMFORT_RISK",
        "MANUAL_RESET",
    ]
    original_action_id: str | None
    fallback_value_c: float | None
    actuator_reset: bool
    simulation_timestamp: datetime


__all__ = [
    "ActionValidationResult",
    "AppliedControlEvent",
    "ExecutableActionCandidate",
    "FallbackEvent",
    "RuntimeTelemetrySnapshot",
]
