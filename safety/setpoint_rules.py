"""Cooling-setpoint identity, bounds, delta, direction, and claim rules."""

import math

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .schemas import SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


_OPTIMALITY_TERMS = ("optimal", "best", "minimum energy")


def evaluate_setpoint_rules(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> tuple[list[SafetyRuleResult], float]:
    requested = candidate.requested_value_c
    current = state.cooling_setpoint_c
    safe_current = (
        candidate.current_value_c if current is None else current
    )
    lower = max(
        settings.minimum_cooling_setpoint_c,
        safe_current - settings.maximum_setpoint_change_c,
    )
    upper = min(
        settings.maximum_cooling_setpoint_c,
        safe_current + settings.maximum_setpoint_change_c,
    )
    clamped = min(max(requested, lower), upper)
    in_range = (
        math.isfinite(requested)
        and settings.minimum_cooling_setpoint_c
        <= requested
        <= settings.maximum_cooling_setpoint_c
    )
    delta_ok = (
        math.isfinite(requested)
        and abs(requested - safe_current)
        <= settings.maximum_setpoint_change_c + 1e-9
    )
    current_matches = (
        current is not None
        and abs(candidate.current_value_c - current)
        <= settings.setpoint_match_tolerance_c
    )
    objective = getattr(candidate, "objective", "maintain_comfort")
    control_type = getattr(candidate, "control_type", "cooling_setpoint")
    reason = str(getattr(candidate, "reason", "") or "")
    energy_direction_valid = not (
        objective in {"reduce_energy", "reduce_peak_demand"}
        and requested < safe_current - 1e-9
    )
    optimality_supported = not any(
        term in reason.casefold() for term in _OPTIMALITY_TERMS
    )

    def rule(code, passed, message, observed, threshold, action="reject"):
        return SafetyRuleResult(
            rule_id=code,
            passed=passed,
            severity="info" if passed else "error",
            message=message,
            observed_value=observed,
            threshold=threshold,
            unit="C" if "SETPOINT" in code else "",
            action=(
                "none"
                if passed
                else "clamp"
                if action == "clamp"
                else action
            ),
        )

    return (
        [
            rule(
                "SETPOINT_OUT_OF_RANGE",
                in_range,
                "Requested cooling setpoint must be inside configured bounds.",
                requested,
                [
                    settings.minimum_cooling_setpoint_c,
                    settings.maximum_cooling_setpoint_c,
                ],
                "clamp",
            ),
            rule(
                "SETPOINT_DELTA_EXCEEDED",
                delta_ok,
                "Requested change must remain within the maximum action delta.",
                requested - safe_current,
                settings.maximum_setpoint_change_c,
                "clamp",
            ),
            rule(
                "CURRENT_SETPOINT_MISMATCH",
                current_matches,
                "Candidate current value must match live Runtime API state.",
                {
                    "candidate": candidate.current_value_c,
                    "live": current,
                },
                settings.setpoint_match_tolerance_c,
            ),
            rule(
                "UNSUPPORTED_CONTROL_TYPE",
                control_type == "cooling_setpoint",
                "Phase 9 controls one cooling-setpoint action only.",
                control_type,
                "cooling_setpoint",
            ),
            rule(
                "ENERGY_REDUCTION_DIRECTION_INVALID",
                energy_direction_valid,
                "Energy-reduction direction cannot lower cooling setpoint.",
                {
                    "objective": objective,
                    "delta_c": requested - safe_current,
                },
                "delta >= 0",
            ),
            rule(
                "UNSUPPORTED_OPTIMALITY_CLAIM",
                optimality_supported,
                "Optimality wording requires a validated candidate comparison.",
                reason,
                "no unsupported optimality language",
            ),
        ],
        clamped,
    )


__all__ = ["evaluate_setpoint_rules"]
