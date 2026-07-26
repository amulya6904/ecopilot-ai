"""Heating/cooling deadband validation with explicit proxy uncertainty."""

from .schemas import SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_deadband(
    state: SafetyStateSnapshot,
    requested_c: float,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> tuple[list[SafetyRuleResult], float]:
    heating = state.heating_setpoint_c
    rules: list[SafetyRuleResult] = []
    if heating is None:
        if not settings.allow_baseline_heating_proxy:
            return (
                [
                    SafetyRuleResult(
                        rule_id="HEATING_SETPOINT_UNAVAILABLE",
                        passed=False,
                        severity="critical",
                        message=(
                            "Heating setpoint is unavailable and proxy use is disabled."
                        ),
                        observed_value=None,
                        threshold=None,
                        unit="C",
                        action="fallback",
                    )
                ],
                requested_c,
            )
        heating = settings.baseline_heating_setpoint_c
        rules.append(
            SafetyRuleResult(
                rule_id="HEATING_SETPOINT_PROXY_USED",
                passed=False,
                severity="warning",
                message=(
                    "Configured Phase 5 baseline heating value is used as an "
                    "explicit proxy because live heating output is unavailable."
                ),
                observed_value=None,
                threshold=heating,
                unit="C",
                action="none",
            )
        )
    minimum = heating + settings.minimum_heating_cooling_deadband_c
    valid = requested_c >= minimum
    clamped = max(requested_c, minimum)
    rules.append(
        SafetyRuleResult(
            rule_id="HEATING_COOLING_DEADBAND_VIOLATION",
            passed=valid,
            severity="info" if valid else "error",
            message="Cooling setpoint must preserve the heating/cooling deadband.",
            observed_value=requested_c,
            threshold=minimum,
            unit="C",
            action="none" if valid else "clamp",
        )
    )
    return rules, clamped


__all__ = ["evaluate_deadband"]
