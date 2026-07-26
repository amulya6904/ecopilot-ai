"""Strict Phase 9 state, rule, decision, recovery, and summary schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictSafetyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SafetyHistoryEntry(StrictSafetyModel):
    action_id: str
    timestamp: datetime
    setpoint_c: float
    decision: str
    zone_name: str


class SafetyHistory(StrictSafetyModel):
    actions: list[SafetyHistoryEntry] = Field(default_factory=list)
    rollback_count: int = Field(default=0, ge=0)
    clamp_count: int = Field(default=0, ge=0)
    reject_count: int = Field(default=0, ge=0)
    telemetry_failure_count: int = Field(default=0, ge=0)


class SafetyStateSnapshot(StrictSafetyModel):
    run_id: str = Field(min_length=1)
    simulation_timestamp: datetime
    wall_clock_timestamp: datetime
    zone_name: str = Field(min_length=1)
    display_zone_name: str = Field(min_length=1)
    zone_role: str = Field(min_length=1)
    occupied: bool
    occupancy_value: float | None
    occupancy_source: str = Field(min_length=1)
    indoor_temperature_c: float | None
    cooling_setpoint_c: float | None
    heating_setpoint_c: float | None
    outdoor_temperature_c: float | None
    relative_humidity_percent: float | None
    pmv: float | None
    ppd_percent: float | None
    facility_demand_kw: float | None
    facility_energy_value: float | None
    telemetry_age_seconds: float = Field(ge=0)
    handles_ready: bool
    actuator_valid: bool
    api_error: bool
    warmup: bool
    current_control_mode: str
    last_action_id: str | None
    last_action_timestamp: datetime | None
    consecutive_agent_failures: int = Field(ge=0)
    consecutive_actuator_failures: int = Field(ge=0)
    recent_setpoints: list[float]
    recent_decisions: list[str]
    severe_runtime_error: bool = False
    fatal_runtime_error: bool = False

    @model_validator(mode="after")
    def validate_timestamps(self) -> "SafetyStateSnapshot":
        for label, value in (
            ("simulation", self.simulation_timestamp),
            ("wall-clock", self.wall_clock_timestamp),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    f"Safety {label} timestamp must be timezone-aware."
                )
        return self


class SafetyRuleResult(StrictSafetyModel):
    rule_id: str = Field(min_length=1)
    passed: bool
    severity: Literal["info", "warning", "error", "critical", "emergency"]
    message: str = Field(min_length=1)
    observed_value: Any = None
    threshold: Any = None
    unit: str = ""
    action: Literal[
        "none", "clamp", "hold", "reject", "fallback", "emergency_fallback"
    ] = "none"


class ComfortEvaluation(StrictSafetyModel):
    comfort_method: Literal["pmv_ppd", "occupied_temperature_proxy"]
    pmv_available: bool
    current_status: Literal[
        "comfortable", "too_hot", "too_cold", "unoccupied", "unknown"
    ]
    safe_headroom_c: float = Field(ge=0)
    risk_level: Literal["low", "medium", "high", "critical"]
    proposed_action_effect: str
    rules: list[SafetyRuleResult]


class DemandAssessment(StrictSafetyModel):
    status: Literal["normal", "warning", "critical", "unavailable"]
    demand_kw: float | None
    rules: list[SafetyRuleResult]


class SafetyDecision(StrictSafetyModel):
    decision_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    decision: Literal[
        "approve",
        "approve_with_clamp",
        "hold",
        "reject",
        "fallback",
        "emergency_fallback",
    ]
    safety_level: Literal["safe", "caution", "unsafe", "critical", "emergency"]
    requested_value_c: float
    approved_value_c: float | None
    violated_rules: list[SafetyRuleResult]
    warnings: list[SafetyRuleResult]
    all_rule_results: list[SafetyRuleResult]
    fallback_required: bool
    emergency_stop_required: bool
    operator_review_required: bool
    validator_version: str
    comfort_method: Literal["pmv_ppd", "occupied_temperature_proxy"]
    pmv_available: bool
    duration_ms: float = Field(ge=0)


class PostActionSafetyResult(StrictSafetyModel):
    verification_id: str
    action_id: str
    approved_value_c: float
    observed_value_c: float | None
    verified_safe: bool
    verified_with_warning: bool
    rollback_required: bool
    emergency_reset_required: bool
    rule_results: list[SafetyRuleResult]
    observed_temperature_c: float | None
    observed_pmv: float | None
    observed_ppd_percent: float | None
    observed_demand_kw: float | None


class RollbackEvent(StrictSafetyModel):
    rollback_id: str
    action_id: str
    reason_code: Literal[
        "SETPOINT_APPLICATION_MISMATCH",
        "COMFORT_LIMIT_BREACH",
        "PMV_LIMIT_BREACH",
        "DEMAND_CRITICAL_AFTER_ACTION",
        "ACTUATOR_VERIFICATION_FAILURE",
        "RUNTIME_ERROR_AFTER_ACTION",
    ]
    reset_attempted: bool
    reset_succeeded: bool
    restored_setpoint_c: float | None
    simulation_timestamp: datetime
    autonomy_disabled: bool


class EmergencyEvent(StrictSafetyModel):
    emergency_id: str
    action_id: str | None
    reason_code: str
    reset_attempted: bool
    baseline_restored: bool
    autonomy_disabled: bool
    operator_acknowledgement_required: bool
    simulation_timestamp: datetime


class SafetyRunSummary(StrictSafetyModel):
    classification: Literal[
        "safety_supervised_energyplus_runtime_validation"
    ] = "safety_supervised_energyplus_runtime_validation"
    safety_supervisor_enabled: Literal[True] = True
    deterministic_safety_authority: Literal[True] = True
    comfort_method: str
    pmv_available: bool
    proposals: int = Field(ge=0)
    approved: int = Field(ge=0)
    clamped: int = Field(ge=0)
    held: int = Field(ge=0)
    rejected: int = Field(ge=0)
    fallbacks: int = Field(ge=0)
    rollbacks: int = Field(ge=0)
    emergency_fallbacks: int = Field(ge=0)
    safety_intervention_rate: float = Field(ge=0, le=1)
    actuator_verification_success_rate: float = Field(ge=0, le=1)
    comfort_violations_prevented: int = Field(ge=0)
    demand_violations_prevented: int = Field(ge=0)
    stale_data_rejections: int = Field(ge=0)
    oscillation_events: int = Field(ge=0)
    severe_count: int = Field(ge=0)
    fatal_count: int = Field(ge=0)
    final_optimization_result: Literal[False] = False
    savings_result: Literal[False] = False


__all__ = [
    "ComfortEvaluation",
    "DemandAssessment",
    "EmergencyEvent",
    "PostActionSafetyResult",
    "RollbackEvent",
    "SafetyDecision",
    "SafetyHistory",
    "SafetyHistoryEntry",
    "SafetyRuleResult",
    "SafetyRunSummary",
    "SafetyStateSnapshot",
]
