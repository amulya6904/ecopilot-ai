"""Deterministic Phase 9 fault scenarios with explicit expectations."""

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .post_action import verify_post_action
from .schemas import (
    SafetyHistory,
    SafetyHistoryEntry,
    SafetyStateSnapshot,
)
from .settings import SAFETY_SETTINGS, SafetySettings
from .supervisor import evaluate_action_safety


NOW = datetime(2013, 1, 1, 12, tzinfo=timezone.utc)


def make_state(**updates: Any) -> SafetyStateSnapshot:
    values: dict[str, Any] = {
        "run_id": "phase9-fault-run",
        "simulation_timestamp": NOW,
        "wall_clock_timestamp": datetime.now(timezone.utc),
        "zone_name": "SPACE1-1",
        "display_zone_name": "Open Office",
        "zone_role": "primary_occupied",
        "occupied": True,
        "occupancy_value": 11.0,
        "occupancy_source": "EnergyPlusRuntime:Zone People Occupant Count",
        "indoor_temperature_c": 23.0,
        "cooling_setpoint_c": 22.0,
        "heating_setpoint_c": 20.0,
        "outdoor_temperature_c": 30.0,
        "relative_humidity_percent": 50.0,
        "pmv": None,
        "ppd_percent": None,
        "facility_demand_kw": 12.0,
        "facility_energy_value": 1000.0,
        "telemetry_age_seconds": 0.0,
        "handles_ready": True,
        "actuator_valid": True,
        "api_error": False,
        "warmup": False,
        "current_control_mode": "mock_agent",
        "last_action_id": None,
        "last_action_timestamp": None,
        "consecutive_agent_failures": 0,
        "consecutive_actuator_failures": 0,
        "recent_setpoints": [],
        "recent_decisions": [],
        "severe_runtime_error": False,
        "fatal_runtime_error": False,
    }
    values.update(updates)
    return SafetyStateSnapshot(**values)


def make_candidate(
    *,
    current: float = 22.0,
    requested: float = 23.0,
    zone: str = "SPACE1-1",
    run_id: str = "phase9-fault-run",
    objective: str = "maintain_comfort",
    reason: str = "deterministic fault-injection candidate",
    action_id: str | None = None,
    effective_from: datetime = NOW,
    effective_until: datetime | None = None,
    expires_at: datetime | None = None,
) -> ExecutableActionCandidate:
    return ExecutableActionCandidate(
        action_id=action_id or f"fault-{uuid.uuid4().hex}",
        source_proposal_id=None,
        source_type="mock_agent",
        zone_name=zone,
        actuator_identifier=(
            "Zone Temperature Control|Cooling Setpoint|SPACE1-1"
        ),
        current_value_c=current,
        requested_value_c=requested,
        requested_delta_c=requested - current,
        effective_from=effective_from,
        effective_until=effective_until or NOW + timedelta(hours=1),
        evidence_references=["fault-injection:deterministic"],
        created_at=NOW,
        expires_at=expires_at or NOW + timedelta(minutes=90),
        run_id=run_id,
        objective=objective,
        reason=reason,
    )


def _history(
    values: list[float],
    *,
    minutes_between: int = 60,
    final_action_id: str | None = None,
) -> SafetyHistory:
    actions = []
    for index, value in enumerate(values):
        age = (len(values) - index) * minutes_between
        actions.append(
            SafetyHistoryEntry(
                action_id=(
                    final_action_id
                    if index == len(values) - 1 and final_action_id
                    else f"history-{index}"
                ),
                timestamp=NOW - timedelta(minutes=age),
                setpoint_c=value,
                decision="approve",
                zone_name="SPACE1-1",
            )
        )
    return SafetyHistory(actions=actions)


def _supervisor_case(
    name: str,
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    history: SafetyHistory,
    expected_outcomes: set[str],
    expected_rule: str,
    settings: SafetySettings,
) -> dict[str, Any]:
    decision = evaluate_action_safety(
        state, candidate, settings=settings, history=history
    )
    failed_or_warning = {
        rule.rule_id
        for rule in decision.all_rule_results
        if not rule.passed
    }
    passed = (
        decision.decision in expected_outcomes
        and expected_rule in failed_or_warning
    )
    return {
        "scenario": name,
        "expected_outcomes": sorted(expected_outcomes),
        "actual_outcome": decision.decision,
        "expected_rule": expected_rule,
        "actual_failed_or_warning_rules": sorted(failed_or_warning),
        "passed": passed,
    }


def run_fault_injection_suite(
    settings: SafetySettings = SAFETY_SETTINGS,
) -> list[dict[str, Any]]:
    cases: list[tuple[Any, ...]] = []

    def add(
        name,
        state,
        candidate,
        expected,
        rule,
        history=None,
    ):
        cases.append(
            (
                name,
                state,
                candidate,
                history or SafetyHistory(),
                set(expected),
                rule,
            )
        )

    add(
        "Unknown zone",
        make_state(),
        make_candidate(zone="UNKNOWN"),
        {"reject"},
        "ZONE_MISMATCH",
    )
    add(
        "Plenum proposal",
        make_state(
            zone_name="PLENUM-1",
            display_zone_name="Plenum",
            zone_role="plenum",
        ),
        make_candidate(zone="PLENUM-1"),
        {"reject"},
        "ZONE_NOT_ELIGIBLE",
    )
    add(
        "Out-of-range setpoint",
        make_state(),
        make_candidate(requested=29.0),
        {"approve_with_clamp"},
        "SETPOINT_OUT_OF_RANGE",
    )
    add(
        "Excessive delta",
        make_state(),
        make_candidate(requested=24.0),
        {"approve_with_clamp"},
        "SETPOINT_DELTA_EXCEEDED",
    )
    add(
        "Deadband conflict",
        make_state(cooling_setpoint_c=23.0, heating_setpoint_c=22.5),
        make_candidate(current=23.0, requested=23.0),
        {"approve_with_clamp"},
        "HEATING_COOLING_DEADBAND_VIOLATION",
    )
    add(
        "Stale telemetry",
        make_state(telemetry_age_seconds=301.0),
        make_candidate(),
        {"fallback"},
        "TELEMETRY_STALE",
    )
    add(
        "Missing temperature",
        make_state(indoor_temperature_c=None),
        make_candidate(),
        {"fallback"},
        "ZONE_TEMPERATURE_MISSING",
    )
    add(
        "Missing setpoint",
        make_state(cooling_setpoint_c=None),
        make_candidate(),
        {"fallback"},
        "SETPOINT_MISSING",
    )
    add(
        "PMV unavailable",
        make_state(pmv=None),
        make_candidate(),
        {"approve"},
        "PMV_UNAVAILABLE_USING_TEMPERATURE_PROXY",
    )
    add(
        "PMV high",
        make_state(pmv=0.8, ppd_percent=25.0),
        make_candidate(),
        {"fallback"},
        "PMV_HOT_LIMIT",
    )
    add(
        "PPD warning",
        make_state(pmv=0.1, ppd_percent=25.0),
        make_candidate(),
        {"approve"},
        "PPD_WARNING_ACTIVE",
    )
    add(
        "Demand warning",
        make_state(facility_demand_kw=24.0),
        make_candidate(),
        {"approve"},
        "DEMAND_WARNING_ACTIVE",
    )
    add(
        "Demand critical",
        make_state(facility_demand_kw=30.0),
        make_candidate(requested=21.0),
        {"reject"},
        "DEMAND_CRITICAL_ACTIVE",
    )
    add(
        "Wrong energy direction",
        make_state(),
        make_candidate(requested=21.0, objective="reduce_energy"),
        {"reject"},
        "ENERGY_REDUCTION_DIRECTION_INVALID",
    )
    hold_id = "fault-hold"
    hold_history = _history(
        [22.0], minutes_between=30, final_action_id=hold_id
    )
    add(
        "Minimum hold violation",
        make_state(
            last_action_id=hold_id,
            last_action_timestamp=hold_history.actions[-1].timestamp,
        ),
        make_candidate(action_id=hold_id),
        {"hold"},
        "MINIMUM_HOLD_NOT_SATISFIED",
        hold_history,
    )
    rate_id = "fault-rate"
    rate_history = _history(
        [22.0, 22.0, 22.0, 22.0],
        minutes_between=10,
        final_action_id=rate_id,
    )
    add(
        "Rate limit",
        make_state(
            last_action_id=rate_id,
            last_action_timestamp=rate_history.actions[-1].timestamp,
        ),
        make_candidate(action_id=rate_id),
        {"hold"},
        "ACTION_RATE_LIMITED",
        rate_history,
    )
    oscillation_history = _history([22.0, 23.0, 22.0], minutes_between=60)
    add(
        "Oscillation",
        make_state(
            cooling_setpoint_c=22.0,
            last_action_id=oscillation_history.actions[-1].action_id,
            last_action_timestamp=oscillation_history.actions[-1].timestamp,
        ),
        make_candidate(current=22.0, requested=23.0),
        {"hold"},
        "ACTION_OSCILLATION_DETECTED",
        oscillation_history,
    )
    add(
        "Actuator invalid",
        make_state(actuator_valid=False),
        make_candidate(),
        {"emergency_fallback"},
        "ACTUATOR_INVALID",
    )
    add(
        "Repeated agent failures",
        make_state(
            consecutive_agent_failures=(
                settings.maximum_consecutive_agent_failures
            )
        ),
        make_candidate(),
        {"emergency_fallback"},
        "REPEATED_AGENT_FAILURES",
    )
    add(
        "Repeated actuator failures",
        make_state(
            consecutive_actuator_failures=(
                settings.maximum_actuator_verification_failures
            )
        ),
        make_candidate(),
        {"emergency_fallback"},
        "REPEATED_ACTUATOR_FAILURES",
    )
    add(
        "Severe runtime error",
        make_state(severe_runtime_error=True),
        make_candidate(),
        {"emergency_fallback"},
        "SEVERE_RUNTIME_ERROR",
    )

    results = [
        _supervisor_case(
            name,
            state,
            candidate,
            history,
            expected,
            rule,
            settings,
        )
        for name, state, candidate, history, expected, rule in cases
    ]
    mismatch_state = make_state()
    mismatch = verify_post_action(
        mismatch_state,
        action_id="fault-write-mismatch",
        approved_value_c=23.0,
        observed_value_c=22.0,
        settings=settings,
    )
    mismatch_rules = {
        rule.rule_id for rule in mismatch.rule_results if not rule.passed
    }
    results.insert(
        18,
        {
            "scenario": "Setpoint write mismatch",
            "expected_outcomes": ["rollback"],
            "actual_outcome": (
                "rollback" if mismatch.rollback_required else "verified"
            ),
            "expected_rule": "SETPOINT_APPLICATION_MISMATCH",
            "actual_failed_or_warning_rules": sorted(mismatch_rules),
            "passed": (
                mismatch.rollback_required
                and "SETPOINT_APPLICATION_MISMATCH" in mismatch_rules
            ),
        },
    )
    return results


__all__ = [
    "make_candidate",
    "make_state",
    "run_fault_injection_suite",
]
