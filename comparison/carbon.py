"""Derived electricity-carbon comparison with explicit intensity assumptions."""

import pandas as pd

from .settings import COMPARISON_SETTINGS, ComparisonSettings


def _intensity(
    timestamps: pd.Series, settings: ComparisonSettings
) -> pd.Series:
    if settings.carbon_intensity_mode == "constant":
        return pd.Series(
            settings.constant_carbon_intensity_g_per_kwh,
            index=timestamps.index,
            dtype=float,
        )
    values = settings.time_varying_carbon_g_per_kwh_by_hour
    if values is None:
        raise ValueError("Time-varying carbon intensities are unavailable.")
    return pd.to_datetime(timestamps).dt.hour.map(
        lambda hour: float(values[int(hour)])
    )


def calculate_carbon_metrics(
    energy_intervals: pd.DataFrame,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> tuple[dict[str, object], pd.DataFrame]:
    frame = energy_intervals[[
        "timestamp", "baseline_energy_kwh", "controlled_energy_kwh"
    ]].copy()
    frame["carbon_intensity_g_per_kwh"] = _intensity(
        frame["timestamp"], settings
    )
    frame["baseline_carbon_kg"] = (
        frame["baseline_energy_kwh"]
        * frame["carbon_intensity_g_per_kwh"]
        / 1000
    )
    frame["controlled_carbon_kg"] = (
        frame["controlled_energy_kwh"]
        * frame["carbon_intensity_g_per_kwh"]
        / 1000
    )
    baseline = float(frame["baseline_carbon_kg"].sum())
    controlled = float(frame["controlled_carbon_kg"].sum())
    reduction = baseline - controlled
    summary: dict[str, object] = {
        "baseline_carbon_kg": baseline,
        "controlled_carbon_kg": controlled,
        "absolute_carbon_reduction_kg": reduction,
        "carbon_reduction_percent": (
            reduction / baseline * 100 if baseline > 0 else None
        ),
        "carbon_intensity_mode": settings.carbon_intensity_mode,
        "carbon_intensity_source": settings.carbon_intensity_source,
        "constant_carbon_intensity_g_per_kwh": (
            settings.constant_carbon_intensity_g_per_kwh
            if settings.carbon_intensity_mode == "constant"
            else None
        ),
        "assumptions": [
            "Carbon is derived from EnergyPlus interval electricity.",
            settings.carbon_intensity_source,
        ],
    }
    return summary, frame


__all__ = ["calculate_carbon_metrics"]
