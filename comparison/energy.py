"""Energy totals and interval/cumulative comparison metrics."""

from typing import Any

import pandas as pd

from .schemas import ComparisonMetric, FacilityMetrics


ENERGY_COLUMNS = (
    ("facility_electricity_kwh", "total_energy_kwh", "Facility electricity"),
    ("hvac_electricity_kwh", "hvac_energy_kwh", "HVAC electricity"),
    ("cooling_electricity_kwh", "cooling_energy_kwh", "Cooling electricity"),
    ("heating_electricity_kwh", "heating_energy_kwh", "Heating electricity"),
    ("fan_electricity_kwh", "fan_energy_kwh", "Fan electricity"),
)


def _optional_sum(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.sum()) if not values.empty else None


def _reduction(
    name: str,
    baseline: float | None,
    controlled: float | None,
    unit: str,
) -> ComparisonMetric:
    available = baseline is not None and controlled is not None
    if not available:
        return ComparisonMetric(
            metric=name,
            baseline=baseline,
            controlled=controlled,
            absolute_reduction=None,
            reduction_percent=None,
            unit=unit,
            available=False,
        )
    absolute = float(baseline - controlled)
    percent = (
        float(absolute / baseline * 100)
        if baseline != 0
        else None
    )
    return ComparisonMetric(
        metric=name,
        baseline=float(baseline),
        controlled=float(controlled),
        absolute_reduction=absolute,
        reduction_percent=percent,
        unit=unit,
        available=True,
    )


def calculate_energy_metrics(
    aligned_facility: pd.DataFrame,
    *,
    occupied_hours: float | None = None,
) -> tuple[
    FacilityMetrics,
    FacilityMetrics,
    list[ComparisonMetric],
    pd.DataFrame,
]:
    """Calculate reductions without clamping zero or negative results."""

    matched = aligned_facility.loc[
        aligned_facility["_merge"] == "both"
    ].copy()
    baseline_values: dict[str, Any] = {}
    controlled_values: dict[str, Any] = {}
    metrics: list[ComparisonMetric] = []
    for source, field, label in ENERGY_COLUMNS:
        baseline = _optional_sum(matched, f"{source}_baseline")
        controlled = _optional_sum(matched, f"{source}_controlled")
        baseline_values[field] = baseline
        controlled_values[field] = controlled
        metrics.append(_reduction(label, baseline, controlled, "kWh"))
    baseline_total = baseline_values["total_energy_kwh"]
    if baseline_total is None or baseline_total <= 0:
        raise ValueError(
            "Baseline facility electricity denominator must be greater than zero."
        )
    controlled_total = controlled_values["total_energy_kwh"]
    if controlled_total is None:
        raise ValueError("Controlled facility electricity is unavailable.")
    baseline_values["energy_per_occupied_hour_kwh"] = (
        float(baseline_total / occupied_hours)
        if occupied_hours and occupied_hours > 0
        else None
    )
    controlled_values["energy_per_occupied_hour_kwh"] = (
        float(controlled_total / occupied_hours)
        if occupied_hours and occupied_hours > 0
        else None
    )
    interval = matched[[
        "timestamp",
        "facility_electricity_kwh_baseline",
        "facility_electricity_kwh_controlled",
    ]].rename(columns={
        "facility_electricity_kwh_baseline": "baseline_energy_kwh",
        "facility_electricity_kwh_controlled": "controlled_energy_kwh",
    })
    interval["interval_energy_reduction_kwh"] = (
        interval["baseline_energy_kwh"] - interval["controlled_energy_kwh"]
    )
    interval["baseline_cumulative_energy_kwh"] = (
        interval["baseline_energy_kwh"].cumsum()
    )
    interval["controlled_cumulative_energy_kwh"] = (
        interval["controlled_energy_kwh"].cumsum()
    )
    interval["cumulative_energy_reduction_kwh"] = (
        interval["baseline_cumulative_energy_kwh"]
        - interval["controlled_cumulative_energy_kwh"]
    )
    interval["date"] = pd.to_datetime(interval["timestamp"]).dt.date.astype(str)
    interval["month"] = (
        pd.to_datetime(interval["timestamp"]).dt.strftime("%Y-%m")
    )
    return (
        FacilityMetrics(**baseline_values),
        FacilityMetrics(**controlled_values),
        metrics,
        interval.reset_index(drop=True),
    )


__all__ = ["calculate_energy_metrics"]
