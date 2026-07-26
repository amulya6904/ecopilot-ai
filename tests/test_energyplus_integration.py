"""Optional real EnergyPlus Phase 4 execution validation."""

import pytest

from backends.energyplus import EnergyPlusBackend
from backends.lightweight import LightweightSimulatorBackend


@pytest.mark.energyplus
def test_real_energyplus_run_when_environment_is_ready() -> None:
    backend = EnergyPlusBackend()
    status = backend.availability_status()
    if not status.ready_for_run:
        pytest.skip(
            "EnergyPlus environment is not ready: "
            + "; ".join(status.readiness_issues)
        )
    assert status.installed
    assert status.executable_found
    assert status.idd_found
    assert status.model_exists
    assert status.weather_exists
    assert status.available
    assert not isinstance(backend, LightweightSimulatorBackend)
    result = backend.run_simulation()
    assert result.exit_code == 0
    assert result.success
    assert result.fatal_count == 0
    assert result.severe_count == 0
    assert result.error_file_path and result.error_file_path.is_file()
    assert result.eso_output_path and result.eso_output_path.is_file()
    assert result.csv_output_path or result.sql_output_path
    assert result.backend == "energyplus"
    assert result.classification == "official_energyplus_simulation"
    assert result.official_result
    assert not result.ai_controlled
    assert not result.closed_loop
    assert not result.optimized
    assert not result.savings_result
    summary = backend.get_telemetry_summary()
    assert summary is not None
    assert summary.zone_temperature_available
    assert summary.outdoor_temperature_available
    assert summary.electricity_available
    assert summary.demand_available
    assert summary.total_electricity_kwh is not None
    assert summary.total_electricity_kwh > 0
    assert summary.peak_demand_kw is not None
    assert summary.peak_demand_kw >= 0
