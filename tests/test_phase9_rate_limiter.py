from datetime import timedelta

from safety.fault_injection import NOW, make_candidate, make_state
from safety.rate_limiter import evaluate_rate_limits
from safety.schemas import SafetyHistory, SafetyHistoryEntry


def _entry(index, minutes, action_id=None):
    return SafetyHistoryEntry(
        action_id=action_id or f"h-{index}",
        timestamp=NOW - timedelta(minutes=minutes),
        setpoint_c=22.0,
        decision="approve",
        zone_name="SPACE1-1",
    )


def test_hold_stale_and_conflict_rules():
    history = SafetyHistory(actions=[_entry(1, 30, "active")])
    candidate = make_candidate(action_id="active")
    rules = evaluate_rate_limits(
        make_state(last_action_id="active"), candidate, history
    )
    assert any(
        item.rule_id == "MINIMUM_HOLD_NOT_SATISFIED"
        and not item.passed
        for item in rules
    )
    stale = make_candidate(
        effective_from=NOW - timedelta(hours=2),
        effective_until=NOW - timedelta(minutes=1),
    )
    rules = evaluate_rate_limits(make_state(), stale, SafetyHistory())
    assert any(item.rule_id == "ACTION_STALE" and not item.passed for item in rules)


def test_hourly_rate_and_active_conflict():
    history = SafetyHistory(
        actions=[_entry(index, 10 * (index + 1)) for index in range(4)]
    )
    rules = evaluate_rate_limits(make_state(), make_candidate(), history)
    assert any(
        item.rule_id == "ACTION_RATE_LIMITED" and not item.passed
        for item in rules
    )
    conflict_history = SafetyHistory(actions=[_entry(1, 30, "old")])
    rules = evaluate_rate_limits(
        make_state(last_action_id="old"),
        make_candidate(action_id="new"),
        conflict_history,
    )
    assert any(
        item.rule_id == "ACTIVE_ACTION_CONFLICT" and not item.passed
        for item in rules
    )
