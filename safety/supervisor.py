"""Final-authority deterministic Phase 9 action-safety evaluation."""

import time
import uuid

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .comfort import evaluate_comfort
from .deadband import evaluate_deadband
from .demand import evaluate_demand
from .emergency import evaluate_emergency_rules
from .oscillation import evaluate_oscillation
from .rate_limiter import evaluate_rate_limits
from .schemas import (
    SafetyDecision,
    SafetyHistory,
    SafetyRuleResult,
    SafetyStateSnapshot,
)
from .setpoint_rules import evaluate_setpoint_rules
from .settings import SAFETY_SETTINGS, SafetySettings
from .telemetry_quality import evaluate_telemetry_quality


SAFETY_VALIDATOR_VERSION = "phase9-safety-supervisor-v1"


def _identity_rules(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
) -> list[SafetyRuleResult]:
    run_matches = candidate.run_id == state.run_id
    return [
        SafetyRuleResult(
            rule_id="RUN_ID_MISMATCH",
            passed=run_matches,
            severity="info" if run_matches else "critical",
            message="Candidate run ID must match the live safety state.",
            observed_value={
                "state": state.run_id,
                "candidate": candidate.run_id,
            },
            threshold=state.run_id,
            unit="",
            action="none" if run_matches else "reject",
        ),
    ]


def _zone_rules(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
) -> list[SafetyRuleResult]:
    eligible = (
        state.zone_role != "plenum"
        and "plenum" not in state.zone_name.casefold()
    )
    matches = state.zone_name == candidate.zone_name
    return [
        SafetyRuleResult(
            rule_id="ZONE_NOT_ELIGIBLE",
            passed=eligible,
            severity="info" if eligible else "critical",
            message="Only the configured occupied non-plenum zone is eligible.",
            observed_value={
                "zone": state.zone_name,
                "role": state.zone_role,
            },
            threshold="occupied non-plenum",
            unit="",
            action="none" if eligible else "reject",
        ),
        SafetyRuleResult(
            rule_id="ZONE_MISMATCH",
            passed=matches,
            severity="info" if matches else "error",
            message="Candidate zone must match the live safety state zone.",
            observed_value={
                "state": state.zone_name,
                "candidate": candidate.zone_name,
            },
            threshold=state.zone_name,
            unit="",
            action="none" if matches else "reject",
        ),
    ]


def _occupancy_rules(
    state: SafetyStateSnapshot,
) -> list[SafetyRuleResult]:
    available = state.occupancy_value is not None
    return [
        SafetyRuleResult(
            rule_id="OCCUPANCY_DATA_UNAVAILABLE",
            passed=available,
            severity="info" if available else "warning",
            message=(
                "Live occupancy determines occupied versus unoccupied comfort "
                "policy; unavailable occupancy is recorded as uncertainty."
            ),
            observed_value={
                "occupied": state.occupied,
                "value": state.occupancy_value,
                "source": state.occupancy_source,
            },
            threshold="genuine occupancy value when available",
            unit="people",
            action="none",
        )
    ]


def _failure_escalation_rules(
    state: SafetyStateSnapshot,
    history: SafetyHistory,
    settings: SafetySettings,
) -> list[SafetyRuleResult]:
    repeated_telemetry = (
        history.telemetry_failure_count >= settings.maximum_missing_samples
    )
    repeated_rollbacks = (
        history.rollback_count >= settings.maximum_rollbacks_before_emergency
    )
    impossible_deadband = (
        state.heating_setpoint_c is not None
        and state.heating_setpoint_c
        + settings.minimum_heating_cooling_deadband_c
        > settings.maximum_cooling_setpoint_c
    )
    conditions = [
        (
            "REPEATED_TELEMETRY_FAILURES",
            repeated_telemetry,
            history.telemetry_failure_count,
            settings.maximum_missing_samples,
        ),
        (
            "REPEATED_ROLLBACK_EVENTS",
            repeated_rollbacks,
            history.rollback_count,
            settings.maximum_rollbacks_before_emergency,
        ),
        (
            "IMPOSSIBLE_DEADBAND_STATE",
            impossible_deadband,
            state.heating_setpoint_c,
            (
                settings.maximum_cooling_setpoint_c
                - settings.minimum_heating_cooling_deadband_c
            ),
        ),
    ]
    return [
        SafetyRuleResult(
            rule_id=rule_id,
            passed=not active,
            severity="emergency" if active else "info",
            message=(
                "Repeated failures or an impossible deadband require baseline "
                "reset, autonomy disablement, and operator acknowledgement."
            ),
            observed_value=observed,
            threshold=threshold,
            unit="",
            action="emergency_fallback" if active else "none",
        )
        for rule_id, active, observed, threshold in conditions
    ]


def evaluate_action_safety(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    settings: SafetySettings = SAFETY_SETTINGS,
    history: SafetyHistory | None = None,
) -> SafetyDecision:
    started = time.perf_counter()
    history = history or SafetyHistory()
    rules: list[SafetyRuleResult] = []

    # Required evaluation order.
    rules.extend(_identity_rules(state, candidate))
    telemetry_rules = evaluate_telemetry_quality(
        state, candidate, settings
    )
    deferred_zone = {"ZONE_MISMATCH"}
    deferred_health = {"ACTUATOR_INVALID", "API_ERROR"}
    rules.extend(
        rule
        for rule in telemetry_rules
        if rule.rule_id not in deferred_zone | deferred_health
    )
    rules.extend(_zone_rules(state, candidate))
    rules.extend(_occupancy_rules(state))
    setpoint_rules, clamped = evaluate_setpoint_rules(
        state, candidate, settings
    )
    rules.extend(setpoint_rules)
    deadband_rules, clamped = evaluate_deadband(
        state, clamped, settings
    )
    rules.extend(deadband_rules)
    rules.extend(
        evaluate_rate_limits(state, candidate, history, settings)
    )
    rules.extend(evaluate_oscillation(candidate, history, settings))
    comfort = evaluate_comfort(state, candidate, settings)
    rules.extend(comfort.rules)
    demand = evaluate_demand(state, candidate, settings)
    rules.extend(demand.rules)
    elevated_demand_headroom_ok = not (
        demand.status in {"warning", "critical"}
        and state.occupied
        and candidate.requested_value_c > candidate.current_value_c
        and (
            candidate.requested_value_c - candidate.current_value_c
            > comfort.safe_headroom_c + 1e-9
        )
    )
    rules.append(
        SafetyRuleResult(
            rule_id="DEMAND_COMFORT_HEADROOM_REQUIRED",
            passed=elevated_demand_headroom_ok,
            severity=(
                "info" if elevated_demand_headroom_ok else "critical"
            ),
            message=(
                "Elevated-demand relaxation requires measured comfort headroom."
            ),
            observed_value={
                "demand_status": demand.status,
                "requested_delta_c": (
                    candidate.requested_value_c
                    - candidate.current_value_c
                ),
                "comfort_headroom_c": comfort.safe_headroom_c,
            },
            threshold="requested delta <= comfort headroom",
            unit="C",
            action=(
                "none" if elevated_demand_headroom_ok else "reject"
            ),
        )
    )
    rules.extend(
        rule
        for rule in telemetry_rules
        if rule.rule_id in deferred_health
    )
    rules.extend(evaluate_emergency_rules(state, settings))
    rules.extend(
        _failure_escalation_rules(state, history, settings)
    )

    initial_failed_actions = [
        rule.action
        for rule in rules
        if not rule.passed and rule.action != "none"
    ]
    clamp_requested = "clamp" in initial_failed_actions
    current = (
        candidate.current_value_c
        if state.cooling_setpoint_c is None
        else state.cooling_setpoint_c
    )
    objective = getattr(candidate, "objective", "maintain_comfort")
    clamp_direction_safe = not (
        objective in {"reduce_energy", "reduce_peak_demand"}
        and clamped < current - 1e-9
    )
    clamp_delta_safe = (
        abs(clamped - current)
        <= settings.maximum_setpoint_change_c + 1e-9
    )
    clamp_bounds_safe = (
        settings.minimum_cooling_setpoint_c
        <= clamped
        <= settings.maximum_cooling_setpoint_c
    )
    clamp_comfort_safe = (
        not state.occupied
        or abs(clamped - current)
        <= comfort.safe_headroom_c + 1e-9
    )
    if clamp_requested:
        clamp_safe = (
            clamp_direction_safe
            and clamp_delta_safe
            and clamp_bounds_safe
            and clamp_comfort_safe
        )
        rules.append(
            SafetyRuleResult(
                rule_id="CLAMP_FINAL_SAFETY_CHECK",
                passed=clamp_safe,
                severity="info" if clamp_safe else "critical",
                message=(
                    "A clamp is allowed only when the nearby value preserves "
                    "direction, delta, bounds, deadband, and comfort headroom."
                ),
                observed_value={
                    "requested_value_c": candidate.requested_value_c,
                    "clamped_value_c": clamped,
                    "direction_safe": clamp_direction_safe,
                    "delta_safe": clamp_delta_safe,
                    "bounds_safe": clamp_bounds_safe,
                    "comfort_headroom_safe": clamp_comfort_safe,
                },
                threshold={
                    "maximum_delta_c": (
                        settings.maximum_setpoint_change_c
                    ),
                    "comfort_headroom_c": comfort.safe_headroom_c,
                },
                unit="C",
                action="none" if clamp_safe else "reject",
            )
        )
    failed_actions = [
        rule.action
        for rule in rules
        if not rule.passed and rule.action != "none"
    ]
    warnings = [
        rule
        for rule in rules
        if not rule.passed and rule.severity == "warning"
    ]
    violated = [
        rule
        for rule in rules
        if not rule.passed and rule.action != "none"
    ]

    if "emergency_fallback" in failed_actions:
        decision = "emergency_fallback"
        level = "emergency"
        approved = None
    elif "fallback" in failed_actions:
        decision = "fallback"
        level = "critical"
        approved = None
    elif "reject" in failed_actions:
        decision = "reject"
        level = "unsafe"
        approved = None
    elif "hold" in failed_actions:
        decision = "hold"
        level = "caution"
        approved = current
    elif clamp_requested:
        decision = "approve_with_clamp"
        level = "caution"
        approved = clamped
    else:
        decision = "approve"
        level = "caution" if warnings else "safe"
        approved = candidate.requested_value_c

    return SafetyDecision(
        decision_id=f"safety-{uuid.uuid4().hex}",
        action_id=candidate.action_id,
        decision=decision,
        safety_level=level,
        requested_value_c=candidate.requested_value_c,
        approved_value_c=approved,
        violated_rules=violated,
        warnings=warnings,
        all_rule_results=rules,
        fallback_required=decision
        in {"fallback", "emergency_fallback"},
        emergency_stop_required=decision == "emergency_fallback",
        operator_review_required=decision
        in {"reject", "fallback", "emergency_fallback"},
        validator_version=SAFETY_VALIDATOR_VERSION,
        comfort_method=comfort.comfort_method,
        pmv_available=comfort.pmv_available,
        duration_ms=(time.perf_counter() - started) * 1000,
    )


__all__ = [
    "SAFETY_VALIDATOR_VERSION",
    "evaluate_action_safety",
]
