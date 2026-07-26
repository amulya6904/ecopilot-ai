from pathlib import Path

import pandas as pd
import pytest

from energyplus.adapter.telemetry import parse_energyplus_outputs


FIXTURE = (
    Path(__file__).parent / "fixtures" / "energyplus" / "phase4_telemetry.csv"
)


def test_building_energy_and_direct_demand_are_converted_once() -> None:
    telemetry = parse_energyplus_outputs(FIXTURE)
    summary = telemetry.summary
    assert len(telemetry.zone) == 2
    assert len(telemetry.building) == 2
    assert summary.electricity_available
    assert summary.demand_available
    assert summary.total_electricity_kwh == pytest.approx(2.6666666667)
    assert summary.peak_demand_kw == pytest.approx(6.0)
    assert telemetry.building["interval_electricity_kwh"].tolist() == pytest.approx(
        [1.0, 1.6666666667]
    )
    assert telemetry.building["facility_demand_kw"].tolist() == pytest.approx(
        [1.0, 6.0]
    )
    assert summary.electricity_source_column == "Electricity:Facility [J](Hourly)"
    assert summary.demand_source_column == (
        "Whole Building:Facility Total Electricity Demand Rate [W](Hourly)"
    )
    assert summary.demand_calculation_method == "direct"
    assert summary.reporting_frequency == "Hourly"
    assert summary.reporting_interval_minutes == 60
    assert not summary.pmv_available
    assert not summary.co2_available


def test_building_total_is_not_multiplied_by_zone_count(tmp_path: Path) -> None:
    raw = pd.read_csv(FIXTURE)
    raw.insert(
        2,
        "SPACE2-1:Zone Mean Air Temperature [C](Hourly)",
        [21.0, 22.0],
    )
    path = tmp_path / "two-zones.csv"
    raw.to_csv(path, index=False)
    telemetry = parse_energyplus_outputs(path)
    assert len(telemetry.zone) == 4
    assert len(telemetry.building) == 2
    assert telemetry.summary.total_electricity_kwh == pytest.approx(2.6666666667)


def test_missing_building_metrics_remain_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "temperature-only.csv"
    pd.DataFrame({
        "Date/Time": ["01/01  01:00:00"],
        "SPACE1-1:Zone Mean Air Temperature [C](Hourly)": [22.0],
        "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)": [30.0],
    }).to_csv(path, index=False)
    summary = parse_energyplus_outputs(path).summary
    assert not summary.electricity_available
    assert not summary.demand_available
    assert summary.total_electricity_kwh is None
    assert summary.peak_demand_kw is None
    assert summary.demand_calculation_method is None


def test_hourly_demand_can_be_derived_from_interval_energy(tmp_path: Path) -> None:
    raw = pd.read_csv(FIXTURE).drop(
        columns=["Whole Building:Facility Total Electricity Demand Rate [W](Hourly)"]
    )
    path = tmp_path / "energy-only.csv"
    raw.to_csv(path, index=False)
    summary = parse_energyplus_outputs(path).summary
    assert summary.demand_available
    assert summary.demand_calculation_method == "derived"
    assert summary.demand_source_column == "Electricity:Facility [J](Hourly)"
    assert summary.peak_demand_kw == pytest.approx(1.6666666667)
