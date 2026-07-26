"""Rollback construction for the verified Phase 8 reset path."""

import uuid

from .schemas import PostActionSafetyResult, RollbackEvent


_ROLLBACK_PRIORITY = (
    "RUNTIME_ERROR_AFTER_ACTION",
    "ACTUATOR_VERIFICATION_FAILURE",
    "COMFORT_LIMIT_BREACH",
    "PMV_LIMIT_BREACH",
    "DEMAND_CRITICAL_AFTER_ACTION",
    "SETPOINT_APPLICATION_MISMATCH",
)


def rollback_reason(verification: PostActionSafetyResult) -> str:
    failed = {
        rule.rule_id for rule in verification.rule_results if not rule.passed
    }
    for reason in _ROLLBACK_PRIORITY:
        if reason in failed:
            return reason
    return "ACTUATOR_VERIFICATION_FAILURE"


def build_rollback_event(
    verification: PostActionSafetyResult,
    *,
    simulation_timestamp,
    reset_attempted: bool,
    reset_succeeded: bool,
    restored_setpoint_c: float | None,
    autonomy_disabled: bool,
) -> RollbackEvent:
    """Record a reset performed through Phase 8, never a second actuator write."""

    return RollbackEvent(
        rollback_id=f"rollback-{uuid.uuid4().hex}",
        action_id=verification.action_id,
        reason_code=rollback_reason(verification),
        reset_attempted=reset_attempted,
        reset_succeeded=reset_succeeded,
        restored_setpoint_c=restored_setpoint_c,
        simulation_timestamp=simulation_timestamp,
        autonomy_disabled=autonomy_disabled,
    )


__all__ = ["build_rollback_event", "rollback_reason"]
