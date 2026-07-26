"""Emergency escalation rules and persisted emergency event construction."""

import uuid

from .schemas import EmergencyEvent, SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_emergency_rules(
    state: SafetyStateSnapshot,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> list[SafetyRuleResult]:
    temperature_emergency = (
        state.indoor_temperature_c is not None
        and not (
            settings.emergency_temperature_min_c
            <= state.indoor_temperature_c
            <= settings.emergency_temperature_max_c
        )
    )
    repeated_actuator = (
        state.consecutive_actuator_failures
        >= settings.maximum_actuator_verification_failures
    )
    repeated_agent = (
        state.consecutive_agent_failures
        >= settings.maximum_consecutive_agent_failures
    )
    runtime_fatal = state.severe_runtime_error or state.fatal_runtime_error
    conditions = [
        (
            "EMERGENCY_TEMPERATURE_LIMIT",
            temperature_emergency,
            state.indoor_temperature_c,
        ),
        (
            "REPEATED_ACTUATOR_FAILURES",
            repeated_actuator,
            state.consecutive_actuator_failures,
        ),
        (
            "REPEATED_AGENT_FAILURES",
            repeated_agent,
            state.consecutive_agent_failures,
        ),
        (
            "SEVERE_RUNTIME_ERROR",
            runtime_fatal,
            {
                "severe": state.severe_runtime_error,
                "fatal": state.fatal_runtime_error,
            },
        ),
    ]
    return [
        SafetyRuleResult(
            rule_id=code,
            passed=not active,
            severity="emergency" if active else "info",
            message=(
                "Emergency condition disables autonomy and requires baseline reset."
            ),
            observed_value=value,
            threshold="configured emergency policy",
            unit="",
            action="emergency_fallback" if active else "none",
        )
        for code, active, value in conditions
    ]


def build_emergency_event(
    state: SafetyStateSnapshot,
    *,
    action_id: str | None,
    reason_code: str,
    reset_attempted: bool,
    baseline_restored: bool,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> EmergencyEvent:
    return EmergencyEvent(
        emergency_id=f"emergency-{uuid.uuid4().hex}",
        action_id=action_id,
        reason_code=reason_code,
        reset_attempted=reset_attempted,
        baseline_restored=baseline_restored,
        autonomy_disabled=settings.emergency_disable_autonomy,
        operator_acknowledgement_required=(
            settings.operator_acknowledgement_required_after_emergency
        ),
        simulation_timestamp=state.simulation_timestamp,
    )


__all__ = ["build_emergency_event", "evaluate_emergency_rules"]
