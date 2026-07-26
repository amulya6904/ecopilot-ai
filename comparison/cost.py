"""Derived electricity-cost comparison with explicit tariff assumptions."""

import pandas as pd

from .settings import COMPARISON_SETTINGS, ComparisonSettings


def _tariff(
    timestamps: pd.Series, settings: ComparisonSettings
) -> pd.Series:
    if settings.electricity_tariff_mode == "flat":
        return pd.Series(
            settings.flat_tariff_per_kwh,
            index=timestamps.index,
            dtype=float,
        )
    values = settings.time_of_use_tariff_by_hour
    if values is None:
        raise ValueError("Time-of-use tariff values are unavailable.")
    return pd.to_datetime(timestamps).dt.hour.map(
        lambda hour: float(values[int(hour)])
    )


def calculate_cost_metrics(
    energy_intervals: pd.DataFrame,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> tuple[dict[str, object], pd.DataFrame]:
    frame = energy_intervals[[
        "timestamp", "baseline_energy_kwh", "controlled_energy_kwh"
    ]].copy()
    frame["tariff_per_kwh"] = _tariff(frame["timestamp"], settings)
    frame["baseline_cost"] = (
        frame["baseline_energy_kwh"] * frame["tariff_per_kwh"]
    )
    frame["controlled_cost"] = (
        frame["controlled_energy_kwh"] * frame["tariff_per_kwh"]
    )
    baseline = float(frame["baseline_cost"].sum())
    controlled = float(frame["controlled_cost"].sum())
    reduction = baseline - controlled
    summary: dict[str, object] = {
        "baseline_cost": baseline,
        "controlled_cost": controlled,
        "absolute_cost_reduction": reduction,
        "cost_reduction_percent": (
            reduction / baseline * 100 if baseline > 0 else None
        ),
        "currency": settings.currency,
        "tariff_mode": settings.electricity_tariff_mode,
        "tariff_source": settings.tariff_source,
        "flat_tariff_per_kwh": (
            settings.flat_tariff_per_kwh
            if settings.electricity_tariff_mode == "flat"
            else None
        ),
        "assumptions": [
            "Electricity cost is derived from EnergyPlus interval electricity.",
            settings.tariff_source,
        ],
    }
    return summary, frame


__all__ = ["calculate_cost_metrics"]
