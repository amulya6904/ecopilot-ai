import csv
from pathlib import Path

import pytest

from scripts.run_phase9_safety_validation import run_validation


@pytest.mark.energyplus_safety
def test_real_energyplus_safety_supervision_and_recovery_artifacts():
    result = run_validation(use_energyplus_when_available=True)
    assert result["success"]
    assert result["energyplus_runtime_available"]
    assert result["energyplus_runtime_executed"]
    assert result["energyplus_runtime_verified"]
    assert result["fault_scenarios_passed"] == 22
    assert result["severe_count"] == 0
    assert result["fatal_count"] == 0
    for key in (
        "phase8_manual_artifact_directory",
        "phase8_clamped_artifact_directory",
    ):
        directory = Path(result[key])
        with (directory / "applied_actions.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        assert rows
        assert all(row["observed_setpoint_after_application"] for row in rows)
        assert all(row["verified"] == "True" for row in rows)
