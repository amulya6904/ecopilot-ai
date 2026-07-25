"""Optional two-run real EnergyPlus Phase 5 acceptance validation."""

from pathlib import Path

import pytest

from energyplus.adapter.discovery import discover_energyplus
from energyplus.baseline.manifest import calculate_sha256
from energyplus.baseline.reproducibility import compare_baseline_runs
from energyplus.baseline.runner import run_energyplus_baseline
from energyplus.baseline.settings import ENERGYPLUS_BASELINE
from config.settings import ENERGYPLUS


@pytest.mark.energyplus
def test_real_phase5_baseline_is_official_and_reproducible() -> None:
    settings = ENERGYPLUS_BASELINE
    source = settings.resolve(settings.base_model_path)
    before = calculate_sha256(source)
    status = discover_energyplus(ENERGYPLUS)
    if not status.ready_for_run:
        pytest.skip(
            "EnergyPlus environment is not ready for the real Phase 5 test: "
            + "; ".join(status.readiness_issues)
        )
    first = run_energyplus_baseline(settings)
    assert first.success, first.failure_reason
    assert calculate_sha256(source) == before
    run = first.energyplus_run_result
    assert run is not None
    assert run.exit_code == 0
    assert run.severe_count == 0
    assert run.fatal_count == 0
    available = first.baseline_summary["actual_available_outputs"]
    assert available["facility_electricity"]
    assert available["facility_demand"]
    assert available["zone_temperature"]
    assert available["cooling_setpoint"]
    assert available["occupancy"] or (
        first.baseline_summary["occupancy_source"] == "schedule_proxy"
    )
    assert (
        available["pmv"]
        or first.baseline_summary["pmv_unavailable_reason"]
    )
    assert first.baseline_summary["thermostat_adherence_percent"] == 100
    assert first.classification == "official_energyplus_baseline"
    assert first.official_result and first.baseline_result
    assert first.backend_id == "energyplus"
    assert first.manifest_path and first.manifest_path.is_file()
    assert all(path.is_file() for path in first.artifact_paths.values())
    second = run_energyplus_baseline(settings)
    assert second.success, second.failure_reason
    report = compare_baseline_runs(
        first, second, settings.reproducibility_tolerance
    )
    assert report.reproducible, report.mismatches
    assert report.exact_input_match
