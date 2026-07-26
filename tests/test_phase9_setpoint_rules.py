from safety.fault_injection import make_candidate, make_state
from safety.setpoint_rules import evaluate_setpoint_rules


def _failed(candidate):
    rules, clamped = evaluate_setpoint_rules(make_state(), candidate)
    return {rule.rule_id for rule in rules if not rule.passed}, clamped


def test_setpoint_bounds_delta_direction_and_current_match():
    failed, clamped = _failed(make_candidate(requested=29.0))
    assert {"SETPOINT_OUT_OF_RANGE", "SETPOINT_DELTA_EXCEEDED"} <= failed
    assert clamped == 23.0
    failed, _ = _failed(
        make_candidate(requested=21.0, objective="reduce_energy")
    )
    assert "ENERGY_REDUCTION_DIRECTION_INVALID" in failed
    failed, _ = _failed(make_candidate(current=21.0, requested=22.0))
    assert "CURRENT_SETPOINT_MISMATCH" in failed


def test_optimality_and_unsupported_control_are_rejected():
    candidate = make_candidate(reason="This is the optimal action")
    failed, _ = _failed(candidate)
    assert "UNSUPPORTED_OPTIMALITY_CLAIM" in failed
    candidate = make_candidate().model_copy(
        update={"control_type": "heating_setpoint"}
    )
    failed, _ = _failed(candidate)
    assert "UNSUPPORTED_CONTROL_TYPE" in failed
