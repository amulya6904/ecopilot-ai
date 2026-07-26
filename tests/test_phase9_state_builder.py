from energyplus.runtime_control.schemas import RuntimeTelemetrySnapshot
from safety.schemas import SafetyHistory
from safety.state_builder import build_safety_state
from tests.phase8_helpers import ready_handles, telemetry


def test_build_state_preserves_genuine_optional_comfort_values():
    runtime = telemetry().model_copy(
        update={
            "relative_humidity_percent": 48.0,
            "pmv": 0.2,
            "ppd_percent": 8.0,
        }
    )
    state = build_safety_state(
        runtime,
        run_id="state-run",
        handles=ready_handles(),
        control_mode="manual",
        history=SafetyHistory(),
    )
    assert state.pmv == 0.2
    assert state.ppd_percent == 8.0
    assert state.occupied
    assert state.occupancy_source.startswith("EnergyPlusRuntime")


def test_build_state_does_not_replace_missing_values_with_zero():
    runtime = telemetry().model_copy(update={"occupancy": None})
    state = build_safety_state(
        runtime,
        run_id="state-run",
        handles=ready_handles(),
        control_mode="manual",
        history=SafetyHistory(),
    )
    assert state.occupancy_value is None
    assert not state.occupied
