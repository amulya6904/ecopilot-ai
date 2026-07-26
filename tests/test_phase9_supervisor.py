from safety.fault_injection import make_candidate, make_state
from safety.schemas import SafetyHistory
from safety.supervisor import evaluate_action_safety


def _decision(state=None, candidate=None):
    return evaluate_action_safety(
        state or make_state(),
        candidate or make_candidate(),
        history=SafetyHistory(),
    )


def test_supervisor_returns_all_six_outcomes():
    values = {
        _decision().decision,
        _decision(candidate=make_candidate(requested=29.0)).decision,
        _decision(state=make_state(warmup=True)).decision,
        _decision(
            candidate=make_candidate(
                requested=21.0, objective="reduce_energy"
            )
        ).decision,
        _decision(
            state=make_state(telemetry_age_seconds=301.0)
        ).decision,
        _decision(
            state=make_state(severe_runtime_error=True)
        ).decision,
    }
    assert values == {
        "approve",
        "approve_with_clamp",
        "hold",
        "reject",
        "fallback",
        "emergency_fallback",
    }


def test_most_severe_rule_wins_and_confidence_cannot_override_it():
    candidate = make_candidate().model_copy(update={"confidence": 1.0})
    result = _decision(
        state=make_state(
            telemetry_age_seconds=301.0,
            severe_runtime_error=True,
        ),
        candidate=candidate,
    )
    assert result.decision == "emergency_fallback"
    assert result.emergency_stop_required


def test_repeated_rollback_telemetry_and_impossible_deadband_escalate():
    for history in (
        SafetyHistory(rollback_count=2),
        SafetyHistory(telemetry_failure_count=2),
    ):
        result = evaluate_action_safety(
            make_state(),
            make_candidate(),
            history=history,
        )
        assert result.decision == "emergency_fallback"
    impossible = evaluate_action_safety(
        make_state(heating_setpoint_c=28.0),
        make_candidate(),
        history=SafetyHistory(),
    )
    assert impossible.decision == "emergency_fallback"
    assert any(
        rule.rule_id == "IMPOSSIBLE_DEADBAND_STATE"
        and not rule.passed
        for rule in impossible.all_rule_results
    )
