import json

import pytest

from energyplus.runtime_control.actuator_discovery import (
    discover_available_actuators,
)
from energyplus.runtime_control.api_loader import inspect_runtime_availability
from energyplus.runtime_control.artifacts import REQUIRED_ARTIFACTS
from energyplus.runtime_control.orchestrator import (
    run_manual_validation,
    run_mock_closed_loop,
)


@pytest.mark.energyplus_runtime
def test_real_runtime_discovery_manual_reset_and_mock_fallback():
    assert inspect_runtime_availability().available
    inventory = discover_available_actuators()
    assert inventory["success"]
    assert inventory["inventory_count"] > 0
    assert inventory["selected_actuator"]["actuator_key"] == "SPACE1-1"
    manual = run_manual_validation()
    assert manual.success
    assert manual.summary["control_injection_verified"]
    assert manual.summary["actuator_reset_verified"]
    mock = run_mock_closed_loop()
    assert mock.success
    assert mock.summary["multiple_intervals_completed"]
    assert mock.summary["fallback_verified"]
    for result in (manual, mock):
        assert result.summary["severe_count"] == 0
        assert result.summary["fatal_count"] == 0
        assert all(
            (result.artifact_directory / name).is_file()
            for name in REQUIRED_ARTIFACTS
        )
        summary = json.loads(
            (result.artifact_directory / "summary.json").read_text(
                encoding="utf-8"
            )
        )
        assert summary["final_optimization_result"] is False
        assert summary["savings_result"] is False
