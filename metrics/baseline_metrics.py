"""Calculated benchmark metrics for Phase 3 baseline simulation results."""

from typing import Any

import pandas as pd

from config.settings import AIR_QUALITY, OPTIMIZATION
from config.zones import ZONES

REQUIRED_COLUMNS = {
    "timestamp", "zone_id", "zone_name", "indoor_temperature_c", "occupancy",
    "co2_ppm", "hvac_power_kw", "interval_energy_kwh",
    "electricity_price_per_kwh", "carbon_intensity_g_per_kwh",
    "comfort_status", "hvac_setpoint_c", "fan_speed_percent",
    "ventilation_level",
}

DEVELOPMENT_RESULT_METADATA: dict[str, str | bool | None] = {
    "data_source": "Lightweight Development Simulator",
    "backend_name": "lightweight",
    "result_classification": "development",
    "pmv_compliance_percent": None,
    "official_energyplus_result": False,
}


def validate_results_dataframe(results: pd.DataFrame) -> None:
    """Reject empty results or results missing fields required by metrics."""
    if results.empty:
        raise ValueError("Results DataFrame must not be empty.")
    missing = REQUIRED_COLUMNS - set(results.columns)
    if missing:
        raise ValueError(f"Results DataFrame is missing columns: {sorted(missing)}")


def _scheduled_occupied_mask(results: pd.DataFrame) -> pd.Series:
    timestamps = pd.to_datetime(results["timestamp"])
    minutes = timestamps.dt.hour * 60 + timestamps.dt.minute
    starts = results["zone_id"].map(
        lambda zone_id: ZONES[zone_id]["normal_start_hour"] * 60
    )
    ends = results["zone_id"].map(
        lambda zone_id: ZONES[zone_id]["normal_end_hour"] * 60
    )
    return (minutes >= starts) & (minutes < ends)


def calculate_energy_metrics(results: pd.DataFrame) -> dict[str, float]:
    """Calculate building energy and power metrics from interval values."""
    validate_results_dataframe(results)
    scheduled = _scheduled_occupied_mask(results)
    return {
        "total_energy_kwh": float(results["interval_energy_kwh"].sum()),
        "average_hvac_power_kw": float(results["hvac_power_kw"].mean()),
        "peak_hvac_power_kw": float(results["hvac_power_kw"].max()),
        "occupied_schedule_energy_kwh": float(
            results.loc[scheduled, "interval_energy_kwh"].sum()
        ),
        "unoccupied_schedule_energy_kwh": float(
            results.loc[~scheduled, "interval_energy_kwh"].sum()
        ),
    }


def calculate_cost_metrics(results: pd.DataFrame) -> dict[str, float]:
    """Calculate time-of-use electricity costs in configured currency units."""
    validate_results_dataframe(results)
    interval_cost = (
        results["interval_energy_kwh"] * results["electricity_price_per_kwh"]
    )
    total_cost = float(interval_cost.sum())
    total_energy = float(results["interval_energy_kwh"].sum())
    peak_price = results["electricity_price_per_kwh"].max()
    return {
        "total_cost_inr": total_cost,
        "peak_price_period_cost_inr": float(
            interval_cost[results["electricity_price_per_kwh"] == peak_price].sum()
        ),
        "average_cost_per_kwh": total_cost / total_energy if total_energy else 0.0,
    }


def _high_carbon_threshold(results: pd.DataFrame) -> float:
    """Use configured high intensity, capped at the run's highest schedule tier."""
    return min(
        OPTIMIZATION.high_carbon_intensity_g_per_kwh,
        float(results["carbon_intensity_g_per_kwh"].max()),
    )


def calculate_carbon_metrics(results: pd.DataFrame) -> dict[str, float]:
    """Calculate energy-weighted carbon emissions."""
    validate_results_dataframe(results)
    emissions_g = (
        results["interval_energy_kwh"] * results["carbon_intensity_g_per_kwh"]
    )
    total_energy = float(results["interval_energy_kwh"].sum())
    high_mask = (
        results["carbon_intensity_g_per_kwh"] >= _high_carbon_threshold(results)
    )
    return {
        "total_carbon_kg": float(emissions_g.sum() / 1000),
        "average_carbon_intensity_g_per_kwh": (
            float(emissions_g.sum() / total_energy) if total_energy else 0.0
        ),
        "high_carbon_period_emissions_kg": float(
            emissions_g[high_mask].sum() / 1000
        ),
    }


def calculate_comfort_metrics(results: pd.DataFrame) -> dict[str, float | int]:
    """Calculate comfort compliance using occupied records only."""
    validate_results_dataframe(results)
    occupied = results.loc[results["occupancy"] > 0]
    total = len(occupied)
    comfortable = int((occupied["comfort_status"] == "Comfortable").sum())
    acceptable = int((occupied["comfort_status"] == "Acceptable").sum())
    uncomfortable = int((occupied["comfort_status"] == "Uncomfortable").sum())
    compliant = comfortable + acceptable
    return {
        "total_occupied_records": total,
        "comfortable_records": comfortable,
        "acceptable_records": acceptable,
        "uncomfortable_records": uncomfortable,
        "comfort_compliant_records": compliant,
        "comfort_compliance_percent": compliant / total * 100 if total else 0.0,
        "comfort_violation_count": uncomfortable,
    }


def calculate_co2_metrics(results: pd.DataFrame) -> dict[str, float | int]:
    """Calculate occupied-only CO2 compliance against configured thresholds."""
    validate_results_dataframe(results)
    occupied = results.loc[results["occupancy"] > 0]
    total = len(occupied)
    within = int((occupied["co2_ppm"] <= AIR_QUALITY.allowed_co2_max_ppm).sum())
    return {
        "average_occupied_co2_ppm": float(occupied["co2_ppm"].mean()) if total else 0.0,
        "maximum_occupied_co2_ppm": float(occupied["co2_ppm"].max()) if total else 0.0,
        "occupied_records_within_allowed_co2": within,
        "allowed_co2_violation_count": int(
            (occupied["co2_ppm"] > AIR_QUALITY.allowed_co2_max_ppm).sum()
        ),
        "warning_co2_violation_count": int(
            (occupied["co2_ppm"] > AIR_QUALITY.warning_co2_max_ppm).sum()
        ),
        "critical_co2_violation_count": int(
            (occupied["co2_ppm"] > AIR_QUALITY.critical_co2_max_ppm).sum()
        ),
        "co2_compliance_percent": within / total * 100 if total else 0.0,
    }


def calculate_baseline_summary(results: pd.DataFrame) -> dict[str, Any]:
    """Combine metrics with explicit development-only result classification."""
    validate_results_dataframe(results)
    facility_power = results.groupby("timestamp")["hvac_power_kw"].sum()
    return {
        "total_records": len(results),
        "total_zones": int(results["zone_id"].nunique()),
        **calculate_energy_metrics(results),
        "peak_demand_kw": float(facility_power.max()),
        **calculate_cost_metrics(results),
        **calculate_carbon_metrics(results),
        **calculate_comfort_metrics(results),
        **calculate_co2_metrics(results),
        "currency_code": OPTIMIZATION.currency_code,
        **DEVELOPMENT_RESULT_METADATA,
    }


def calculate_zone_summary(results: pd.DataFrame) -> pd.DataFrame:
    """Return energy, environment, comfort, and CO2 metrics for each zone."""
    validate_results_dataframe(results)
    rows: list[dict[str, Any]] = []
    for zone_id in ZONES:
        zone = results.loc[results["zone_id"] == zone_id]
        if zone.empty:
            continue
        comfort = calculate_comfort_metrics(zone)
        co2 = calculate_co2_metrics(zone)
        interval_cost = zone["interval_energy_kwh"] * zone["electricity_price_per_kwh"]
        interval_carbon = (
            zone["interval_energy_kwh"] * zone["carbon_intensity_g_per_kwh"]
        )
        rows.append({
            "zone_id": zone_id,
            "zone_name": str(zone["zone_name"].iloc[0]),
            "data_source": DEVELOPMENT_RESULT_METADATA["data_source"],
            "backend_name": DEVELOPMENT_RESULT_METADATA["backend_name"],
            "result_classification": DEVELOPMENT_RESULT_METADATA[
                "result_classification"
            ],
            "official_energyplus_result": False,
            "pmv_compliance_percent": None,
            "total_energy_kwh": float(zone["interval_energy_kwh"].sum()),
            "total_cost_inr": float(interval_cost.sum()),
            "total_carbon_kg": float(interval_carbon.sum() / 1000),
            "average_hvac_power_kw": float(zone["hvac_power_kw"].mean()),
            "peak_hvac_power_kw": float(zone["hvac_power_kw"].max()),
            "average_indoor_temperature_c": float(zone["indoor_temperature_c"].mean()),
            "minimum_indoor_temperature_c": float(zone["indoor_temperature_c"].min()),
            "maximum_indoor_temperature_c": float(zone["indoor_temperature_c"].max()),
            "average_co2_ppm": float(zone["co2_ppm"].mean()),
            "maximum_co2_ppm": float(zone["co2_ppm"].max()),
            "occupied_records": comfort["total_occupied_records"],
            "comfort_compliance_percent": comfort["comfort_compliance_percent"],
            "comfort_violation_count": comfort["comfort_violation_count"],
            "co2_compliance_percent": co2["co2_compliance_percent"],
            "allowed_co2_violation_count": co2["allowed_co2_violation_count"],
        })
    return pd.DataFrame(rows)
