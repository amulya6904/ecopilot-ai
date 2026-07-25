from pathlib import Path

import pandas as pd
import pytest

from energyplus.baseline.settings import EnergyPlusBaselineSettings
from energyplus.baseline.metrics import calculate_baseline_metrics
from energyplus.baseline.normalizer import NormalizedBaselineTelemetry


def _settings(tmp_path: Path) -> EnergyPlusBaselineSettings:
    return EnergyPlusBaselineSettings(
        repository_root=tmp_path,
        base_model_path=Path("energyplus/models/modified/source.idf"),
        baseline_model_path=Path("energyplus/models/baseline/baseline.idf"),
        weather_file_path=Path("energyplus/weather/weather.epw"),
        official_output_root=Path("energyplus/output/official/baseline"),
        official_results_root=Path("results/official"),
        metadata_root=Path("energyplus/metadata/baseline"),
    )


def _telemetry(*, pmv: bool = True, occupancy: bool = True):
    times = pd.to_datetime([
        "2000-01-01 09:00", "2000-01-01 10:00",
        "2000-01-01 18:00", "2000-01-01 19:00",
    ])
    rows = []
    space_occupancy = [0, 1, 1, 1] if occupancy else [None] * 4
    for index, timestamp in enumerate(times):
        rows.append({
            "timestamp": timestamp,
            "energyplus_zone_name": "SPACE1-1",
            "display_zone_name": "Open Office",
            "zone_role": "primary_occupied",
            "indoor_temperature_c": [21, 23, 26, 24][index],
            "cooling_setpoint_c": [27, 22, 22, 27][index],
            "heating_setpoint_c": [16, 20, 20, 16][index],
            "occupancy": space_occupancy[index],
            "relative_humidity_percent": 50,
            "pmv": [None, 0.1, 0.6, -0.2][index] if pmv else None,
            "ppd_percent": [None, 5, 15, 7][index] if pmv else None,
            "outdoor_temperature_c": 30,
            "backend": "energyplus",
            "source": "EnergyPlus",
            "classification": "official_energyplus_baseline",
            "official_result": True,
            "baseline_result": True,
        })
        rows.append({
            **rows[-1],
            "energyplus_zone_name": "PLENUM-1",
            "display_zone_name": "HVAC Plenum",
            "zone_role": "plenum",
            "indoor_temperature_c": 40,
            "cooling_setpoint_c": 0,
            "heating_setpoint_c": 0,
            "occupancy": 10 if occupancy else None,
            "pmv": 4 if pmv else None,
            "ppd_percent": 100 if pmv else None,
        })
    facility = pd.DataFrame({
        "timestamp": times,
        "facility_electricity_kwh": [1, 1, 1, 1],
        "facility_demand_kw": [1, 2, 5, 3],
        "hvac_electricity_kwh": [0.5] * 4,
        "cooling_electricity_kwh": [0.25] * 4,
        "heating_electricity_kwh": [None] * 4,
        "fan_electricity_kwh": [0.1] * 4,
        "outdoor_temperature_c": [30] * 4,
        "backend": ["energyplus"] * 4,
        "source": ["EnergyPlus"] * 4,
        "classification": ["official_energyplus_baseline"] * 4,
        "official_result": [True] * 4,
        "baseline_result": [True] * 4,
    })
    return NormalizedBaselineTelemetry(
        zone=pd.DataFrame(rows),
        facility=facility,
        actual_available_outputs={},
        source_columns=(),
    )


def test_energy_demand_comfort_pmv_and_adherence(tmp_path: Path) -> None:
    metrics = calculate_baseline_metrics(_telemetry(), _settings(tmp_path))
    summary = metrics.summary
    assert summary["total_facility_electricity_kwh"] == 4
    assert summary["total_hvac_electricity_kwh"] == 2
    assert summary["total_cooling_electricity_kwh"] == 1
    assert summary["total_heating_electricity_kwh"] is None
    assert summary["average_facility_demand_kw"] == pytest.approx(2.75)
    assert summary["peak_facility_demand_kw"] == 5
    assert summary["peak_demand_timestamp"] == "2000-01-01T18:00:00"
    assert summary["total_occupied_conditioned_records"] == 3
    assert summary["temperature_compliance_percent"] == pytest.approx(200 / 3)
    assert summary["high_temperature_violation_count"] == 1
    assert summary["pmv_available"]
    assert summary["pmv_compliance_percent"] == pytest.approx(200 / 3)
    assert summary["thermostat_adherence_percent"] == 100
    plenum = metrics.zone_summary.query(
        "energyplus_zone_name == 'PLENUM-1'"
    ).iloc[0]
    assert plenum["occupied_records"] == 0
    assert pd.isna(plenum["temperature_compliance_percent"])
    assert not any(
        "electricity" in column or column.startswith("total_energy")
        for column in metrics.zone_summary.columns
    )


def test_missing_pmv_is_explicitly_unavailable(tmp_path: Path) -> None:
    summary = calculate_baseline_metrics(
        _telemetry(pmv=False), _settings(tmp_path)
    ).summary
    assert not summary["pmv_available"]
    assert summary["pmv_compliance_percent"] is None
    assert summary["pmv_violation_count"] is None
    assert summary["pmv_unavailable_reason"]


def test_missing_occupancy_uses_labelled_schedule_proxy(tmp_path: Path) -> None:
    summary = calculate_baseline_metrics(
        _telemetry(occupancy=False), _settings(tmp_path)
    ).summary
    assert not summary["occupancy_available"]
    assert summary["occupancy_source"] == "schedule_proxy"
    assert summary["total_occupied_conditioned_records"] == 2


def test_zero_occupied_records_are_safe(tmp_path: Path) -> None:
    telemetry = _telemetry()
    telemetry.zone.loc[
        telemetry.zone["energyplus_zone_name"] == "SPACE1-1", "occupancy"
    ] = 0
    summary = calculate_baseline_metrics(
        telemetry, _settings(tmp_path)
    ).summary
    assert summary["total_occupied_conditioned_records"] == 0
    assert summary["temperature_compliance_percent"] is None
