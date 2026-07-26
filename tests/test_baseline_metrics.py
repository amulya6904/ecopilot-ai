"""Controlled formula tests for Phase 3 metrics."""

import pandas as pd
import pytest

from metrics.baseline_metrics import (
    calculate_carbon_metrics,
    calculate_comfort_metrics,
    calculate_cost_metrics,
    calculate_energy_metrics,
    calculate_co2_metrics,
    calculate_zone_summary,
    validate_results_dataframe,
)


def _results() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-07-25 09:00", "2026-07-25 09:05", "2026-07-25 18:00"]),
        "zone_id": ["office"] * 3, "zone_name": ["Open Office"] * 3,
        "indoor_temperature_c": [23, 24.5, 27], "occupancy": [2, 2, 0],
        "co2_ppm": [900, 1600, 2000], "hvac_power_kw": [6, 3, 1],
        "interval_energy_kwh": [0.5, 0.25, 0.1],
        "cumulative_energy_kwh": [0.5, 0.75, 0.85],
        "electricity_price_per_kwh": [10, 10, 8],
        "carbon_intensity_g_per_kwh": [650, 650, 450],
        "comfort_status": ["Comfortable", "Acceptable", "Unoccupied"],
        "hvac_setpoint_c": [22, 22, 27], "fan_speed_percent": [80, 80, 20],
        "ventilation_level": ["medium", "medium", "low"],
    })


def test_energy_cost_and_carbon_formulas() -> None:
    frame = _results()
    assert calculate_energy_metrics(frame)["total_energy_kwh"] == pytest.approx(0.85)
    assert calculate_cost_metrics(frame)["total_cost_inr"] == pytest.approx(8.3)
    assert calculate_carbon_metrics(frame)["total_carbon_kg"] == pytest.approx(0.5325)


def test_occupied_only_compliance_and_thresholds() -> None:
    frame = _results()
    comfort = calculate_comfort_metrics(frame)
    assert comfort["total_occupied_records"] == 2
    assert comfort["comfort_compliance_percent"] == 100
    co2 = calculate_co2_metrics(frame)
    assert co2["co2_compliance_percent"] == 50
    assert co2["allowed_co2_violation_count"] == 1
    assert co2["warning_co2_violation_count"] == 1
    assert co2["critical_co2_violation_count"] == 1


def test_zero_occupancy_validation_and_zone_columns() -> None:
    frame = _results()
    frame["occupancy"] = 0
    assert calculate_comfort_metrics(frame)["comfort_compliance_percent"] == 0
    assert calculate_co2_metrics(frame)["co2_compliance_percent"] == 0
    expected = {"zone_id", "total_energy_kwh", "total_cost_inr", "total_carbon_kg",
                "comfort_compliance_percent", "co2_compliance_percent"}
    assert expected <= set(calculate_zone_summary(frame).columns)
    with pytest.raises(ValueError, match="empty"):
        validate_results_dataframe(frame.iloc[0:0])
    with pytest.raises(ValueError, match="missing"):
        validate_results_dataframe(frame.drop(columns=["co2_ppm"]))
