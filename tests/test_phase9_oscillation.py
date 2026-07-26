from datetime import timedelta

from safety.fault_injection import NOW, make_candidate
from safety.oscillation import evaluate_oscillation
from safety.schemas import SafetyHistory, SafetyHistoryEntry


def _history(values):
    return SafetyHistory(
        actions=[
            SafetyHistoryEntry(
                action_id=f"a-{index}",
                timestamp=NOW - timedelta(hours=len(values) - index),
                setpoint_c=value,
                decision="approve",
                zone_name="SPACE1-1",
            )
            for index, value in enumerate(values)
        ]
    )


def test_alternation_and_direction_reversal_are_detected():
    rule = evaluate_oscillation(
        make_candidate(current=22.0, requested=23.0),
        _history([22.0, 23.0, 22.0]),
    )[0]
    assert not rule.passed
    assert rule.rule_id == "ACTION_OSCILLATION_DETECTED"


def test_stable_history_is_safe():
    rule = evaluate_oscillation(
        make_candidate(current=22.0, requested=22.0),
        _history([22.0, 22.0, 22.0]),
    )[0]
    assert rule.passed
