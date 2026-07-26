"""Isolated Phase 6 fixtures; normal tests never execute EnergyPlus."""

from dataclasses import replace
import json
from pathlib import Path

import pandas as pd
import pytest

from energyplus.baseline.runner import EnergyPlusBaselineRunResult
from mcp_service.context import MCPApplicationContext
from mcp_service.settings import MCPSettings


class ReadyBackend:
    def availability_status(self):
        from energyplus.adapter.discovery import EnergyPlusAvailability
        return EnergyPlusAvailability(
            installed=True, available=True, ready_for_run=True,
            executable_found=True, executable_path=None, installation_dir=None,
            idd_path=None, idd_found=True, detected_version="26.1.0",
            expected_version="26.1", version_compatible=True, model_exists=True,
            weather_exists=True, output_root_ready=True, reason=None,
            readiness_issues=(),
        )


@pytest.fixture
def phase6_context(tmp_path: Path) -> MCPApplicationContext:
    root = tmp_path / "repo"
    results = root / "results" / "official"
    results.mkdir(parents=True)
    summary = {
        "run_id": "fixture-run", "success": True, "backend": "energyplus",
        "source": "EnergyPlus", "classification": "official_energyplus_baseline",
        "official_result": True, "baseline_result": True,
        "total_facility_electricity_kwh": 3.0,
        "total_hvac_electricity_kwh": 1.0,
        "total_cooling_electricity_kwh": 0.5,
        "total_heating_electricity_kwh": 0.0,
        "total_fan_electricity_kwh": 0.5,
        "average_facility_demand_kw": 1.5,
        "peak_facility_demand_kw": 2.0,
        "peak_demand_timestamp": "2000-01-01T02:00:00",
        "reporting_interval_count": 2,
        "total_occupied_conditioned_records": 2,
        "occupancy_source": "energyplus_people_output",
        "temperature_compliant_records": 1,
        "temperature_compliance_percent": 50.0,
        "temperature_violation_count": 1,
        "low_temperature_violation_count": 1,
        "high_temperature_violation_count": 0,
        "minimum_occupied_temperature_c": 21.0,
        "maximum_occupied_temperature_c": 23.0,
        "pmv_available": False,
        "pmv_unavailable_reason": "Fixture has no PMV.",
        "minimum_occupied_pmv": None, "maximum_occupied_pmv": None,
        "pmv_compliance_percent": None, "average_occupied_ppd_percent": None,
        "thermostat_adherence_percent": 100.0, "mismatching_records": 0,
        "actual_available_outputs": {
            "zone_temperature": True, "cooling_setpoint": True,
            "heating_setpoint": True, "occupancy": True,
            "zone_relative_humidity": True, "pmv": False, "ppd": False,
            "outdoor_temperature": True, "facility_electricity": True,
            "facility_demand": True,
        },
    }
    (results / "phase5_energyplus_baseline_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    manifest = {
        "run_id": "fixture-run", "executable_path": "C:/secret/energyplus.exe",
        "base_model_hash": "a" * 64, "weather_hash": "b" * 64,
        "thermostat_policy": {}, "zone_display_mapping": {"SPACE1-1": "Open Office"},
    }
    (results / "phase5_energyplus_baseline_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    errors = {
        "run_id": "fixture-run", "warning_count": 1, "severe_count": 0,
        "fatal_count": 0, "records": [{
            "severity": "warning", "classification": "reporting_issue",
            "message": "Fixture warning", "recoverable": True,
            "raw_log_excerpt": "do not expose",
        }],
    }
    (results / "phase5_energyplus_baseline_errors.json").write_text(json.dumps(errors), encoding="utf-8")
    zone = pd.DataFrame([
        {"timestamp": "2000-01-01T09:00:00", "energyplus_zone_name": "SPACE1-1",
         "display_zone_name": "Open Office", "zone_role": "primary_occupied",
         "indoor_temperature_c": 21.0, "cooling_setpoint_c": 27.0,
         "heating_setpoint_c": 16.0, "occupancy": 1.0,
         "relative_humidity_percent": 50.0, "pmv": None, "ppd_percent": None},
        {"timestamp": "2000-01-01T10:00:00", "energyplus_zone_name": "SPACE1-1",
         "display_zone_name": "Open Office", "zone_role": "primary_occupied",
         "indoor_temperature_c": 23.0, "cooling_setpoint_c": 22.0,
         "heating_setpoint_c": 20.0, "occupancy": 1.0,
         "relative_humidity_percent": 51.0, "pmv": None, "ppd_percent": None},
        {"timestamp": "2000-01-01T09:00:00", "energyplus_zone_name": "PLENUM-1",
         "display_zone_name": "HVAC Plenum", "zone_role": "plenum",
         "indoor_temperature_c": 25.0, "cooling_setpoint_c": None,
         "heating_setpoint_c": None, "occupancy": 0.0,
         "relative_humidity_percent": 49.0, "pmv": None, "ppd_percent": None},
    ])
    zone.to_csv(results / "phase5_energyplus_baseline_zone_telemetry.csv", index=False)
    pd.DataFrame([
        {"timestamp": "2000-01-01T01:00:00", "interval_electricity_kwh": 1.0,
         "facility_demand_kw": 1.0, "outdoor_temperature_c": 30.0},
        {"timestamp": "2000-01-01T02:00:00", "interval_electricity_kwh": 2.0,
         "facility_demand_kw": 2.0, "outdoor_temperature_c": 31.0},
    ]).to_csv(results / "phase5_energyplus_baseline_facility_telemetry.csv", index=False)
    pd.DataFrame([
        {"energyplus_zone_name": "SPACE1-1", "display_zone_name": "Open Office",
         "zone_role": "primary_occupied", "temperature_compliance_percent": 50.0,
         "pmv_available": False},
        {"energyplus_zone_name": "PLENUM-1", "display_zone_name": "HVAC Plenum",
         "zone_role": "plenum", "temperature_compliance_percent": None,
         "pmv_available": False},
    ]).to_csv(results / "phase5_energyplus_baseline_zone_summary.csv", index=False)
    settings = MCPSettings(repository_root=root)
    baseline_settings = replace(
        __import__("energyplus.baseline.settings", fromlist=["ENERGYPLUS_BASELINE"]).ENERGYPLUS_BASELINE,
        repository_root=root,
    )
    def runner(*args, **kwargs):
        return EnergyPlusBaselineRunResult(
            run_id="mock-run", success=True, official_result=True,
            baseline_result=True, baseline_summary=summary,
            artifact_paths={"summary": results / "phase5_energyplus_baseline_summary.json"},
        )
    return MCPApplicationContext(
        settings=settings, baseline_settings=baseline_settings,
        backend_factory=ReadyBackend, baseline_runner=runner,
    )
