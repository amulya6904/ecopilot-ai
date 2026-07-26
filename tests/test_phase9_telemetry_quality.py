from safety.fault_injection import make_candidate, make_state
from safety.telemetry_quality import evaluate_telemetry_quality


def _failed(state):
    return {
        item.rule_id
        for item in evaluate_telemetry_quality(state, make_candidate())
        if not item.passed
    }


def test_required_missing_and_stale_values_are_detected():
    assert "ZONE_TEMPERATURE_MISSING" in _failed(
        make_state(indoor_temperature_c=None)
    )
    assert "SETPOINT_MISSING" in _failed(
        make_state(cooling_setpoint_c=None)
    )
    assert "TELEMETRY_STALE" in _failed(
        make_state(telemetry_age_seconds=301.0)
    )


def test_invalid_numeric_and_runtime_health_are_detected():
    assert "INVALID_NUMERIC_VALUE" in _failed(make_state(pmv=float("nan")))
    failed = _failed(make_state(api_error=True, actuator_valid=False))
    assert {"API_ERROR", "ACTUATOR_INVALID"} <= failed
