from pathlib import Path

import pandas as pd
import pytest

from energyplus.baseline.settings import EnergyPlusBaselineSettings
from energyplus.baseline.normalizer import (
    normalize_energyplus_baseline_csv,
    parse_energyplus_timestamp,
)


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


def _raw() -> pd.DataFrame:
    return pd.DataFrame({
        "Date/Time": ["01/01  23:00:00", "01/01  24:00:00"],
        "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)": [30, 29],
        "SPACE1-1:Zone Mean Air Temperature [C](Hourly)": [24, 23],
        "PLENUM-1:Zone Mean Air Temperature [C](Hourly)": [27, 26],
        "SPACE1-1:Zone Thermostat Cooling Setpoint Temperature [C](Hourly)": [27, 27],
        "PLENUM-1:Zone Thermostat Cooling Setpoint Temperature [C](Hourly)": [0, 0],
        "SPACE1-1:Zone Thermostat Heating Setpoint Temperature [C](Hourly)": [16, 16],
        "SPACE1-1:Zone People Occupant Count [](Hourly)": [1, 0],
        "SPACE1-1:Zone Air Relative Humidity [%](Hourly)": [50, 51],
        "Electricity:Facility [J](Hourly)": [3_600_000, 7_200_000],
        "Whole Building:Facility Total Electricity Demand Rate [W](Hourly)": [1000, 2000],
        "Electricity:HVAC [J](Hourly)": [1_800_000, 3_600_000],
    })


def test_zone_identity_mapping_nulls_and_stable_sort(tmp_path: Path) -> None:
    path = tmp_path / "eplusout.csv"
    _raw().to_csv(path, index=False)
    telemetry = normalize_energyplus_baseline_csv(path, _settings(tmp_path))
    assert telemetry.zone["energyplus_zone_name"].drop_duplicates().tolist() == [
        "PLENUM-1", "SPACE1-1"
    ]
    space = telemetry.zone[
        telemetry.zone["energyplus_zone_name"] == "SPACE1-1"
    ]
    plenum = telemetry.zone[
        telemetry.zone["energyplus_zone_name"] == "PLENUM-1"
    ]
    assert space["display_zone_name"].iloc[0] == "Open Office"
    assert space["zone_role"].iloc[0] == "primary_occupied"
    assert plenum["zone_role"].iloc[0] == "plenum"
    assert telemetry.zone["pmv"].isna().all()
    assert telemetry.zone["ppd_percent"].isna().all()
    assert not telemetry.zone.duplicated(
        ["timestamp", "energyplus_zone_name"]
    ).any()
    assert telemetry.zone["timestamp"].is_monotonic_increasing


def test_facility_values_are_converted_once_not_multiplied_by_zones(
    tmp_path: Path,
) -> None:
    path = tmp_path / "eplusout.csv"
    _raw().to_csv(path, index=False)
    telemetry = normalize_energyplus_baseline_csv(path, _settings(tmp_path))
    assert len(telemetry.facility) == 2
    assert telemetry.facility["facility_electricity_kwh"].sum() == pytest.approx(3)
    assert telemetry.facility["facility_demand_kw"].tolist() == [1, 2]
    assert telemetry.facility["hvac_electricity_kwh"].sum() == pytest.approx(1.5)


def test_timestamp_24_hour_rolls_forward() -> None:
    assert parse_energyplus_timestamp("12/31  24:00:00") == pd.Timestamp(
        "2001-01-01 00:00:00"
    )
    assert parse_energyplus_timestamp("01/01  01:00:00") == pd.Timestamp(
        "2000-01-01 01:00:00"
    )


def test_duplicate_facility_timestamps_are_rejected(tmp_path: Path) -> None:
    raw = _raw()
    raw.loc[1, "Date/Time"] = raw.loc[0, "Date/Time"]
    path = tmp_path / "duplicates.csv"
    raw.to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate facility"):
        normalize_energyplus_baseline_csv(path, _settings(tmp_path))


def test_missing_occupancy_remains_null(tmp_path: Path) -> None:
    raw = _raw().drop(
        columns=["SPACE1-1:Zone People Occupant Count [](Hourly)"]
    )
    path = tmp_path / "no-occupancy.csv"
    raw.to_csv(path, index=False)
    telemetry = normalize_energyplus_baseline_csv(path, _settings(tmp_path))
    assert telemetry.zone["occupancy"].isna().all()
    assert not telemetry.actual_available_outputs["occupancy"]
