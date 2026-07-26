"""Alternating setpoint and repeated intervention detection."""

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .schemas import SafetyHistory, SafetyRuleResult
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_oscillation(
    candidate: ExecutableActionCandidate,
    history: SafetyHistory,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> list[SafetyRuleResult]:
    values = [entry.setpoint_c for entry in history.actions[-5:]]
    values.append(candidate.requested_value_c)
    directions = [
        1 if right > left else -1 if right < left else 0
        for left, right in zip(values, values[1:])
    ]
    nonzero = [value for value in directions if value]
    reversals = sum(
        left != right for left, right in zip(nonzero, nonzero[1:])
    )
    alternating = (
        len(values) >= 4
        and abs(values[-1] - values[-3]) <= 1e-6
        and abs(values[-2] - values[-4]) <= 1e-6
        and abs(values[-1] - values[-2]) > 1e-6
    )
    excessive_interventions = (
        history.clamp_count + history.reject_count
        >= settings.maximum_actions_per_zone_per_hour
    )
    detected = (
        alternating
        or reversals >= settings.oscillation_reversal_limit
        or excessive_interventions
    )
    return [
        SafetyRuleResult(
            rule_id="ACTION_OSCILLATION_DETECTED",
            passed=not detected,
            severity="error" if detected else "info",
            message=(
                "Alternation, frequent direction reversal, or repeated clamp/"
                "reject cycles triggers a deterministic hold."
            ),
            observed_value={
                "setpoints": values,
                "reversals": reversals,
                "interventions": (
                    history.clamp_count + history.reject_count
                ),
            },
            threshold={
                "reversal_limit": settings.oscillation_reversal_limit,
                "intervention_limit": (
                    settings.maximum_actions_per_zone_per_hour
                ),
            },
            unit="",
            action="hold" if detected else "none",
        )
    ]


__all__ = ["evaluate_oscillation"]
