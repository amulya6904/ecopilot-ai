"""Deterministic verification after a supervised actuator application."""

import uuid

from .schemas import (
    PostActionSafetyResult,
    SafetyRuleResult,
    SafetyStateSnapshot,
)
from .settings import SAFETY_SETTINGS, SafetySettings


def _result(
    rule_id: str,
    passed: bool,
    message: str,
    *,
    observed=None,
    threshold=None,
    severity: str = "critical",
    action: str = "reject",
    unit: str = "",
) -> SafetyRuleResult:
    return SafetyRuleResult(
        rule_id=rule_id,
        passed=passed,
        severity="info" if passed else severity,
        message=message,
        observed_value=observed,
        threshold=threshold,
        unit=unit,
        action="none" if passed else action,
    )


def verify_post_action(
    state: SafetyStateSnapshot,
    *,
    action_id: str,
    approved_value_c: float,
    observed_value_c: float | None,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> PostActionSafetyResult:
    """Verify the one linked write without predicting unobserved outcomes."""

    setpoint_matches = (
        observed_value_c is not None
        and abs(observed_value_c - approved_value_c)
        <= settings.setpoint_match_tolerance_c
    )
    temperature_safe = (
        state.indoor_temperature_c is not None
        and settings.emergency_temperature_min_c
        <= state.indoor_temperature_c
        <= settings.emergency_temperature_max_c
    )
    pmv_safe = (
        state.pmv is None
        or not state.occupied
        or settings.pmv_min <= state.pmv <= settings.pmv_max
    )
    ppd_critical = (
        state.ppd_percent is not None
        and state.occupied
        and state.ppd_percent > settings.ppd_critical_percent
    )
    demand_safe = (
        state.facility_demand_kw is None
        or state.facility_demand_kw < settings.demand_critical_kw
    )
    telemetry_fresh = (
        state.telemetry_age_seconds
        <= settings.maximum_telemetry_age_seconds
    )
    actuator_healthy = (
        state.handles_ready and state.actuator_valid and not state.api_error
    )
    runtime_healthy = not (
        state.severe_runtime_error or state.fatal_runtime_error
    )
    rules = [
        _result(
            "SETPOINT_APPLICATION_MISMATCH",
            setpoint_matches,
            "Observed cooling setpoint must match the approved value.",
            observed={
                "approved_value_c": approved_value_c,
                "observed_value_c": observed_value_c,
            },
            threshold=settings.setpoint_match_tolerance_c,
            unit="C",
        ),
        _result(
            "COMFORT_LIMIT_BREACH",
            temperature_safe,
            "Indoor temperature must remain inside emergency limits.",
            observed=state.indoor_temperature_c,
            threshold=[
                settings.emergency_temperature_min_c,
                settings.emergency_temperature_max_c,
            ],
            action="emergency_fallback",
            unit="C",
        ),
        _result(
            "PMV_LIMIT_BREACH",
            pmv_safe,
            "Genuine occupied PMV must remain within configured limits.",
            observed=state.pmv,
            threshold=[settings.pmv_min, settings.pmv_max],
            unit="PMV",
        ),
        _result(
            "PPD_CRITICAL_AFTER_ACTION",
            not ppd_critical,
            "Occupied PPD must not exceed the critical project policy.",
            observed=state.ppd_percent,
            threshold=settings.ppd_critical_percent,
            severity="error",
            unit="%",
        ),
        _result(
            "DEMAND_CRITICAL_AFTER_ACTION",
            demand_safe,
            "Facility demand must remain below the prototype critical threshold.",
            observed=state.facility_demand_kw,
            threshold=settings.demand_critical_kw,
            unit="kW",
        ),
        _result(
            "TELEMETRY_STALE",
            telemetry_fresh,
            "Post-action telemetry must remain fresh.",
            observed=state.telemetry_age_seconds,
            threshold=settings.maximum_telemetry_age_seconds,
            unit="s",
        ),
        _result(
            "ACTUATOR_VERIFICATION_FAILURE",
            actuator_healthy,
            "Actuator handles and the Data Exchange API must remain healthy.",
            observed={
                "handles_ready": state.handles_ready,
                "actuator_valid": state.actuator_valid,
                "api_error": state.api_error,
            },
            threshold="healthy",
            action="emergency_fallback",
        ),
        _result(
            "RUNTIME_ERROR_AFTER_ACTION",
            runtime_healthy,
            "No severe or fatal EnergyPlus runtime error may follow an action.",
            observed={
                "severe": state.severe_runtime_error,
                "fatal": state.fatal_runtime_error,
            },
            threshold=False,
            action="emergency_fallback",
        ),
    ]
    failures = [rule for rule in rules if not rule.passed]
    emergency = any(
        rule.action == "emergency_fallback" for rule in failures
    )
    warnings = (
        state.pmv is None
        or state.facility_demand_kw is None
        or state.ppd_percent is None
    )
    return PostActionSafetyResult(
        verification_id=f"post-{uuid.uuid4().hex}",
        action_id=action_id,
        approved_value_c=approved_value_c,
        observed_value_c=observed_value_c,
        verified_safe=not failures,
        verified_with_warning=not failures and warnings,
        rollback_required=bool(failures),
        emergency_reset_required=emergency,
        rule_results=rules,
        observed_temperature_c=state.indoor_temperature_c,
        observed_pmv=state.pmv,
        observed_ppd_percent=state.ppd_percent,
        observed_demand_kw=state.facility_demand_kw,
    )


__all__ = ["verify_post_action"]
