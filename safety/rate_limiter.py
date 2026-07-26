"""Staleness, minimum hold, action-rate, and conflict constraints."""

from datetime import timedelta

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .schemas import SafetyHistory, SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_rate_limits(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    history: SafetyHistory,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> list[SafetyRuleResult]:
    now = state.simulation_timestamp
    stale = now > candidate.expires_at or not (
        candidate.effective_from <= now <= candidate.effective_until
    )
    recent = [
        action
        for action in history.actions
        if now - action.timestamp <= timedelta(hours=1)
        and action.zone_name == state.zone_name
    ]
    last = history.actions[-1] if history.actions else None
    changes_value = (
        state.cooling_setpoint_c is not None
        and abs(
            candidate.requested_value_c - state.cooling_setpoint_c
        )
        > settings.setpoint_match_tolerance_c
    )
    hold_ok = (
        last is None
        or not changes_value
        or (now - last.timestamp).total_seconds()
        >= settings.minimum_hold_minutes * 60
    )
    rate_ok = len(recent) < settings.maximum_actions_per_zone_per_hour
    conflict = (
        state.last_action_id is not None
        and state.last_action_id != candidate.action_id
        and not hold_ok
    )

    def result(code, passed, message, observed, threshold, action):
        return SafetyRuleResult(
            rule_id=code,
            passed=passed,
            severity="info" if passed else "error",
            message=message,
            observed_value=observed,
            threshold=threshold,
            unit="",
            action="none" if passed else action,
        )

    return [
        result(
            "ACTION_STALE",
            not stale,
            "Candidate must be fresh and inside its effective window.",
            now.isoformat(),
            candidate.expires_at.isoformat(),
            "fallback",
        ),
        result(
            "MINIMUM_HOLD_NOT_SATISFIED",
            hold_ok,
            "Setpoint changes must respect the minimum hold duration.",
            (
                None
                if last is None
                else (now - last.timestamp).total_seconds() / 60
            ),
            settings.minimum_hold_minutes,
            "hold",
        ),
        result(
            "ACTION_RATE_LIMITED",
            rate_ok,
            "Zone action count must remain below the hourly rate limit.",
            len(recent),
            settings.maximum_actions_per_zone_per_hour,
            "hold",
        ),
        result(
            "ACTIVE_ACTION_CONFLICT",
            not conflict,
            "A conflicting action cannot replace an active held action.",
            {
                "active": state.last_action_id,
                "candidate": candidate.action_id,
            },
            "no conflict",
            "reject",
        ),
    ]


__all__ = ["evaluate_rate_limits"]
