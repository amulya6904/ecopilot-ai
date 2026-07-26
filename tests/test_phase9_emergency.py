from safety.emergency import build_emergency_event, evaluate_emergency_rules
from safety.fault_injection import make_state


def test_emergency_temperature_failures_and_runtime_errors_escalate():
    rules = evaluate_emergency_rules(
        make_state(
            indoor_temperature_c=36.0,
            consecutive_actuator_failures=2,
            severe_runtime_error=True,
        )
    )
    failed = {item.rule_id for item in rules if not item.passed}
    assert {
        "EMERGENCY_TEMPERATURE_LIMIT",
        "REPEATED_ACTUATOR_FAILURES",
        "SEVERE_RUNTIME_ERROR",
    } <= failed
    assert all(
        item.action == "emergency_fallback"
        for item in rules
        if not item.passed
    )


def test_emergency_event_disables_autonomy_and_requires_acknowledgement():
    state = make_state()
    event = build_emergency_event(
        state,
        action_id="a",
        reason_code="SEVERE_RUNTIME_ERROR",
        reset_attempted=True,
        baseline_restored=True,
    )
    assert event.autonomy_disabled
    assert event.operator_acknowledgement_required
