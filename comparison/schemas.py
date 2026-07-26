"""Strict Phase 10 identities, metrics, claim, and reproducibility models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RunIdentity(StrictComparisonModel):
    run_id: str
    mode: str
    backend: str
    source: str
    classification: str
    model_path: str
    base_model_hash: str
    derived_model_hash: str
    weather_path: str
    weather_hash: str
    energyplus_version: str
    run_period: list[Any]
    reporting_frequency: str
    interval_count: int = Field(ge=0)
    zone_mapping_hash: str
    occupancy_configuration_hash: str
    internal_load_configuration_hash: str | None
    control_policy: str
    severe_count: int = Field(ge=0)
    fatal_count: int = Field(ge=0)
    success: bool
    critical_telemetry_complete: bool
    control_injection_verified: bool
    safety_supervisor_enabled: bool


class CompatibilityCheck(StrictComparisonModel):
    check_id: str
    passed: bool
    required: bool
    baseline_value: Any = None
    controlled_value: Any = None
    message: str


class CompatibilityReport(StrictComparisonModel):
    status: Literal[
        "comparable", "conditionally_comparable", "not_comparable"
    ]
    comparable: bool
    conditionally_comparable: bool
    checks: list[CompatibilityCheck]
    failed_required_checks: list[str]
    warnings: list[str]


class FacilityMetrics(StrictComparisonModel):
    total_energy_kwh: float
    hvac_energy_kwh: float | None
    cooling_energy_kwh: float | None
    heating_energy_kwh: float | None
    fan_energy_kwh: float | None
    energy_per_occupied_hour_kwh: float | None


class ComfortMetrics(StrictComparisonModel):
    occupied_records: int = Field(ge=0)
    temperature_compliant_records: int = Field(ge=0)
    temperature_compliance_percent: float | None
    low_temperature_violations: int = Field(ge=0)
    high_temperature_violations: int = Field(ge=0)
    maximum_deviation_c: float | None
    average_occupied_temperature_c: float | None
    degree_hours_outside_comfort: float
    pmv_available: bool
    pmv_compliance_percent: float | None
    average_pmv: float | None
    maximum_absolute_pmv: float | None
    average_ppd_percent: float | None
    maximum_ppd_percent: float | None
    comfort_method: Literal["pmv_ppd", "occupied_temperature_proxy"]


class ReliabilityMetrics(StrictComparisonModel):
    expected_intervals: int = Field(ge=0)
    completed_intervals: int = Field(ge=0)
    completion_percent: float
    llm_requests: int = Field(ge=0)
    llm_responses: int = Field(ge=0)
    llm_timeouts: int = Field(ge=0)
    mcp_calls: int = Field(ge=0)
    mcp_failures: int = Field(ge=0)
    valid_structured_outputs: int = Field(ge=0)
    invalid_structured_outputs: int = Field(ge=0)
    proposals: int = Field(ge=0)
    approvals: int = Field(ge=0)
    clamps: int = Field(ge=0)
    holds: int = Field(ge=0)
    rejections: int = Field(ge=0)
    applied_actions: int = Field(ge=0)
    verified_actuator_changes: int = Field(ge=0)
    fallbacks: int = Field(ge=0)
    rollbacks: int = Field(ge=0)
    emergency_fallbacks: int = Field(ge=0)
    severe_count: int = Field(ge=0)
    fatal_count: int = Field(ge=0)
    average_llm_latency_ms: float | None
    average_mcp_latency_ms: float | None
    average_safety_latency_ms: float | None


class AgentMetrics(StrictComparisonModel):
    average_tool_calls_per_decision: float
    structured_output_success_rate: float | None
    self_corrections: int = Field(ge=0)
    average_proposal_confidence: float | None
    decisions_using_official_energyplus_evidence: int = Field(ge=0)
    total_decisions: int = Field(ge=0)


class SafetyMetrics(StrictComparisonModel):
    intervention_rate: float
    unsafe_actions_prevented: int = Field(ge=0)
    comfort_risk_actions_prevented: int = Field(ge=0)
    demand_risk_actions_prevented: int = Field(ge=0)
    stale_data_rejections: int = Field(ge=0)
    oscillation_detections: int = Field(ge=0)
    actuator_mismatches: int = Field(ge=0)
    rollback_success_rate: float | None
    emergency_recovery_success_rate: float | None


class ComparisonMetric(StrictComparisonModel):
    metric: str
    baseline: float | None
    controlled: float | None
    absolute_reduction: float | None
    reduction_percent: float | None
    unit: str
    available: bool


class ClaimGateResult(StrictComparisonModel):
    claim_status: Literal[
        "validated_positive_savings",
        "energy_reduced_comfort_not_maintained",
        "comfort_maintained_no_energy_savings",
        "negative_energy_savings",
        "comparison_invalid",
        "comparison_incomplete",
    ]
    eligible_to_claim_savings: bool
    reasons: list[str]
    warnings: list[str]
    approved_statement: str


class ComparisonSummary(StrictComparisonModel):
    comparison_id: str
    comparison_valid: bool
    claim_status: str
    eligible_to_claim_savings: bool
    baseline_energy_kwh: float | None
    controlled_energy_kwh: float | None
    energy_reduction_kwh: float | None
    energy_reduction_percent: float | None
    baseline_peak_demand_kw: float | None
    controlled_peak_demand_kw: float | None
    peak_reduction_percent: float | None
    baseline_comfort_percent: float | None
    controlled_comfort_percent: float | None
    comfort_gate_passed: bool
    cost_reduction: float | None
    carbon_reduction: float | None
    severe_count: int
    fatal_count: int
    official_energyplus_comparison: bool
    safety_supervisor_enabled: bool
    control_injection_verified: bool
    telemetry_alignment_passed: bool
    reproducible: bool
    exact_approved_statement: str
    assumptions: list[str]
    limitations: list[str]


class ReproducibilityReport(StrictComparisonModel):
    reproducible: bool
    mode: str
    first_comparison_id: str
    second_comparison_id: str | None
    model_hashes_match: bool
    weather_hashes_match: bool
    telemetry_shape_match: bool
    energy_within_tolerance: bool
    peak_demand_within_tolerance: bool
    comfort_within_tolerance: bool
    action_counts_match: bool
    comparison_status_match: bool
    mismatches: list[str]
    limitations: list[str]
    tolerance: float


__all__ = [
    "AgentMetrics",
    "ClaimGateResult",
    "ComfortMetrics",
    "ComparisonMetric",
    "ComparisonSummary",
    "CompatibilityCheck",
    "CompatibilityReport",
    "FacilityMetrics",
    "ReliabilityMetrics",
    "ReproducibilityReport",
    "RunIdentity",
    "SafetyMetrics",
]
