"""Required, finite, fresh, identity-bound Runtime API telemetry checks."""

import math

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .schemas import SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def _rule(
    code: str,
    passed: bool,
    message: str,
    *,
    observed=None,
    threshold=None,
    severity: str = "error",
    action: str = "fallback",
    unit: str = "",
) -> SafetyRuleResult:
    return SafetyRuleResult(
        rule_id=code,
        passed=passed,
        severity="info" if passed else severity,
        message=message,
        observed_value=observed,
        threshold=threshold,
        unit=unit,
        action="none" if passed else action,
    )


def evaluate_telemetry_quality(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> list[SafetyRuleResult]:
    rules: list[SafetyRuleResult] = []
    rules.append(
        _rule(
            "ZONE_TEMPERATURE_MISSING",
            state.indoor_temperature_c is not None,
            "Zone temperature is required and is never replaced with zero.",
            observed=state.indoor_temperature_c,
        )
    )
    rules.append(
        _rule(
            "SETPOINT_MISSING",
            state.cooling_setpoint_c is not None,
            "Live cooling setpoint is required.",
            observed=state.cooling_setpoint_c,
        )
    )
    numeric_values = {
        "indoor_temperature_c": state.indoor_temperature_c,
        "cooling_setpoint_c": state.cooling_setpoint_c,
        "heating_setpoint_c": state.heating_setpoint_c,
        "outdoor_temperature_c": state.outdoor_temperature_c,
        "relative_humidity_percent": state.relative_humidity_percent,
        "pmv": state.pmv,
        "ppd_percent": state.ppd_percent,
        "facility_demand_kw": state.facility_demand_kw,
    }
    invalid = [
        name
        for name, value in numeric_values.items()
        if value is not None
        and (
            isinstance(value, bool)
            or not math.isfinite(float(value))
        )
    ]
    rules.append(
        _rule(
            "INVALID_NUMERIC_VALUE",
            not invalid,
            "All available numeric telemetry must be finite.",
            observed=invalid,
            severity="critical",
            action="emergency_fallback",
        )
    )
    rules.append(
        _rule(
            "TELEMETRY_STALE",
            state.telemetry_age_seconds
            <= settings.maximum_telemetry_age_seconds,
            "Telemetry age must remain inside the freshness limit.",
            observed=state.telemetry_age_seconds,
            threshold=settings.maximum_telemetry_age_seconds,
            unit="s",
        )
    )
    rules.append(
        _rule(
            "ACTUATOR_INVALID",
            state.handles_ready and state.actuator_valid,
            "Required handles and the selected actuator must be valid.",
            observed={
                "handles_ready": state.handles_ready,
                "actuator_valid": state.actuator_valid,
            },
            severity="critical",
            action="emergency_fallback",
        )
    )
    rules.append(
        _rule(
            "API_ERROR",
            not state.api_error,
            "The EnergyPlus Data Exchange API error flag must be clear.",
            observed=state.api_error,
            severity="critical",
            action="emergency_fallback",
        )
    )
    rules.append(
        _rule(
            "ZONE_MISMATCH",
            state.zone_name == candidate.zone_name,
            "Candidate zone must match the live safety state zone.",
            observed={
                "state": state.zone_name,
                "candidate": candidate.zone_name,
            },
            action="reject",
        )
    )
    rules.append(
        _rule(
            "WARMUP_NOT_CONTROLLABLE",
            not state.warmup,
            "Warmup timesteps are excluded from control.",
            observed=state.warmup,
            action="hold",
        )
    )
    plausible_temperature = (
        state.indoor_temperature_c is None
        or -20 <= state.indoor_temperature_c <= 60
    )
    plausible_setpoint = (
        state.cooling_setpoint_c is None
        or 5 <= state.cooling_setpoint_c <= 45
    )
    rules.append(
        _rule(
            "INVALID_NUMERIC_VALUE",
            plausible_temperature and plausible_setpoint,
            "Temperatures and setpoints must be physically plausible.",
            observed={
                "temperature": state.indoor_temperature_c,
                "setpoint": state.cooling_setpoint_c,
            },
            severity="critical",
            action="emergency_fallback",
        )
    )
    return rules


__all__ = ["evaluate_telemetry_quality"]
