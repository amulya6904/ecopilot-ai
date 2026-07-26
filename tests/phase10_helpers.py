"""Compact fixture builders shared by the Phase 10 unit tests."""

import json
from pathlib import Path

import pandas as pd

from comparison.artifact_loader import stable_json_hash
from comparison.normalization import normalize_facility, normalize_zone
from comparison.schemas import RunIdentity
from comparison.settings import ComparisonSettings


def make_identity(kind: str = "baseline", **updates) -> RunIdentity:
    controlled = kind == "controlled"
    values = {
        "run_id": f"{kind}-run",
        "mode": "reproducible_policy" if controlled else "baseline",
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": (
            "official_energyplus_safety_supervised_controlled_evaluation"
            if controlled
            else "official_energyplus_baseline"
        ),
        "model_path": "model.idf",
        "base_model_hash": "a" * 64,
        "derived_model_hash": "b" * 64,
        "weather_path": "weather.epw",
        "weather_hash": "c" * 64,
        "energyplus_version": "26.1.0",
        "run_period": ["RunPeriod", "Run Period 1", "1", "1", "12", "31"],
        "reporting_frequency": "Hourly",
        "interval_count": 2,
        "zone_mapping_hash": "d" * 64,
        "occupancy_configuration_hash": "e" * 64,
        "internal_load_configuration_hash": "f" * 64,
        "control_policy": (
            "phase10-reproducible-policy-v1" if controlled else "fixed_schedule"
        ),
        "severe_count": 0,
        "fatal_count": 0,
        "success": True,
        "critical_telemetry_complete": True,
        "control_injection_verified": controlled,
        "safety_supervisor_enabled": controlled,
    }
    values.update(updates)
    return RunIdentity(**values)


def facility_frame(
    energies=(10.0, 10.0), demands=(4.0, 6.0)
) -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": ["2000-01-01T01:00:00", "2000-01-01T02:00:00"],
        "facility_electricity_kwh": energies,
        "facility_demand_kw": demands,
        "hvac_electricity_kwh": [2.0, 2.0],
        "cooling_electricity_kwh": [1.0, 1.0],
        "heating_electricity_kwh": [0.0, 0.0],
        "fan_electricity_kwh": [1.0, 1.0],
        "outdoor_temperature_c": [30.0, 31.0],
    })


def zone_frame(
    temperatures=(22.0, 26.0),
    occupancies=(1.0, 1.0),
    pmv=(None, None),
    ppd=(None, None),
) -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": ["2000-01-01T01:00:00", "2000-01-01T02:00:00"],
        "energyplus_zone_name": ["SPACE1-1", "SPACE1-1"],
        "display_zone_name": ["Open Office", "Open Office"],
        "zone_role": ["primary_occupied", "primary_occupied"],
        "occupancy": occupancies,
        "indoor_temperature_c": temperatures,
        "cooling_setpoint_c": [22.0, 22.0],
        "heating_setpoint_c": [20.0, 20.0],
        "relative_humidity_percent": [50.0, 51.0],
        "pmv": pmv,
        "ppd_percent": ppd,
    })


def aligned_frames(
    baseline_energy=(10.0, 10.0),
    controlled_energy=(9.0, 9.0),
    baseline_temperature=(22.0, 26.0),
    controlled_temperature=(22.5, 24.0),
):
    from comparison.alignment import align_telemetry

    baseline_facility = normalize_facility(
        facility_frame(baseline_energy), run_id="base", classification="base"
    )
    controlled_facility = normalize_facility(
        facility_frame(controlled_energy), run_id="ctrl", classification="ctrl"
    )
    baseline_zone = normalize_zone(
        zone_frame(baseline_temperature), run_id="base"
    )
    controlled_zone = normalize_zone(
        zone_frame(controlled_temperature), run_id="ctrl"
    )
    return align_telemetry(
        baseline_facility,
        controlled_facility,
        baseline_zone,
        controlled_zone,
        expected_intervals=2,
    )


def make_artifact_fixture(root: Path) -> tuple[ComparisonSettings, Path, Path]:
    official = root / "results" / "official"
    controlled = root / "results" / "closed_loop" / "phase8" / "controlled-run"
    official.mkdir(parents=True)
    controlled.mkdir(parents=True)
    inventory = [{"schedule": "OCCUPY-1"}]
    loads = {"people": ["OCCUPY-1"], "lights": ["LIGHTS-1"]}
    outputs = {
        "zone_temperature": True,
        "cooling_setpoint": True,
        "occupancy": True,
        "outdoor_temperature": True,
        "facility_electricity": True,
        "facility_demand": True,
    }
    baseline_manifest = {
        "run_id": "baseline-run",
        "base_model_path": "base.idf",
        "base_model_hash": "a" * 64,
        "derived_baseline_model_path": "derived.idf",
        "derived_model_hash": "b" * 64,
        "weather_path": "weather.epw",
        "weather_hash": "c" * 64,
        "energyplus_version": "26.1.0",
        "run_period": ["RunPeriod", "Run Period 1"],
        "reporting_frequency": "Hourly",
        "zone_display_mapping": {"SPACE1-1": "Open Office"},
        "occupancy_schedule_inventory": inventory,
        "internal_load_schedule_inventory": loads,
        "actual_available_outputs": outputs,
    }
    baseline_summary = {
        "run_id": "baseline-run",
        "mode": "baseline",
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": "official_energyplus_baseline",
        "official_result": True,
        "baseline_result": True,
        "success": True,
        "base_model_hash": "a" * 64,
        "derived_model_hash": "b" * 64,
        "weather_hash": "c" * 64,
        "energyplus_version": "26.1.0",
        "reporting_frequency": "Hourly",
        "reporting_interval_count": 2,
        "severe_count": 0,
        "fatal_count": 0,
        "pmv_available": False,
    }
    (official / "phase5_energyplus_baseline_manifest.json").write_text(
        json.dumps(baseline_manifest), encoding="utf-8"
    )
    (official / "phase5_energyplus_baseline_summary.json").write_text(
        json.dumps(baseline_summary), encoding="utf-8"
    )
    facility_frame().to_csv(
        official / "phase5_energyplus_baseline_facility_telemetry.csv",
        index=False,
    )
    zone_frame().to_csv(
        official / "phase5_energyplus_baseline_zone_telemetry.csv",
        index=False,
    )
    controlled_manifest = {
        "run_id": "controlled-run",
        "backend": "energyplus",
        "source": "EnergyPlus",
        "base_model_hash": "a" * 64,
        "runtime_model_path": "derived.idf",
        "runtime_model_hash": "b" * 64,
        "weather_path": "weather.epw",
        "weather_hash": "c" * 64,
        "energyplus_version": "26.1.0",
        "run_period": ["RunPeriod", "Run Period 1"],
        "reporting_frequency": "Hourly",
        "interval_count": 2,
        "zone_display_mapping": {"SPACE1-1": "Open Office"},
        "zone_mapping_hash": stable_json_hash({"SPACE1-1": "Open Office"}),
        "occupancy_schedule_inventory": inventory,
        "occupancy_configuration_hash": stable_json_hash(inventory),
        "internal_load_schedule_inventory": loads,
        "internal_load_configuration_hash": stable_json_hash(loads),
        "control_policy": "phase10-reproducible-policy-v1",
        "actual_available_outputs": outputs,
        "files": {
            "facility_telemetry": "controlled_facility_telemetry.csv",
            "zone_telemetry": "controlled_zone_telemetry.csv",
            "actions": "controlled_action_summary.csv",
            "safety_summary": "controlled_safety_summary.json",
        },
    }
    controlled_summary = {
        "run_id": "controlled-run",
        "mode": "reproducible_policy",
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": (
            "official_energyplus_safety_supervised_controlled_evaluation"
        ),
        "success": True,
        "base_model_hash": "a" * 64,
        "derived_model_hash": "b" * 64,
        "weather_hash": "c" * 64,
        "energyplus_version": "26.1.0",
        "reporting_frequency": "Hourly",
        "reporting_interval_count": 2,
        "severe_count": 0,
        "fatal_count": 0,
        "control_injection_verified": True,
        "safety_supervisor_enabled": True,
        "complete_horizon": True,
        "actual_available_outputs": outputs,
    }
    (controlled / "controlled_manifest.json").write_text(
        json.dumps(controlled_manifest), encoding="utf-8"
    )
    (controlled / "controlled_summary.json").write_text(
        json.dumps(controlled_summary), encoding="utf-8"
    )
    facility_frame((9.0, 9.0)).to_csv(
        controlled / "controlled_facility_telemetry.csv", index=False
    )
    zone_frame((22.5, 24.0)).to_csv(
        controlled / "controlled_zone_telemetry.csv", index=False
    )
    pd.DataFrame([{
        "timestamp": "2000-01-01T01:00:00",
        "proposal_id": "p",
        "action_id": "a",
        "requested_setpoint_c": 22.5,
        "approved_setpoint_c": 22.5,
        "applied_setpoint_c": 22.5,
        "observed_setpoint_c": 22.5,
        "decision": "approve",
        "safety_level": "safe",
        "fallback": False,
        "rollback": False,
    }]).to_csv(controlled / "controlled_action_summary.csv", index=False)
    (controlled / "controlled_safety_summary.json").write_text(
        json.dumps({}), encoding="utf-8"
    )
    settings = ComparisonSettings(repository_root=root)
    return settings, official, controlled

