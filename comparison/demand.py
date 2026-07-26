"""Facility demand and threshold-exceedance comparison."""

import pandas as pd

from .settings import COMPARISON_SETTINGS, ComparisonSettings


def _side(
    frame: pd.DataFrame,
    suffix: str,
    settings: ComparisonSettings,
) -> dict[str, object]:
    column = f"facility_demand_kw_{suffix}"
    values = pd.to_numeric(frame[column], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return {
            "peak_demand_kw": None,
            "peak_timestamp": None,
            "average_demand_kw": None,
            "intervals_above_warning": 0,
            "intervals_above_critical": 0,
        }
    index = valid.idxmax()
    return {
        "peak_demand_kw": float(valid.max()),
        "peak_timestamp": pd.Timestamp(frame.loc[index, "timestamp"]).isoformat(),
        "average_demand_kw": float(valid.mean()),
        "intervals_above_warning": int(
            (valid >= settings.demand_warning_kw).sum()
        ),
        "intervals_above_critical": int(
            (valid >= settings.demand_critical_kw).sum()
        ),
    }


def calculate_demand_metrics(
    aligned_facility: pd.DataFrame,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> tuple[dict[str, object], pd.DataFrame]:
    matched = aligned_facility.loc[
        aligned_facility["_merge"] == "both"
    ].copy()
    baseline = _side(matched, "baseline", settings)
    controlled = _side(matched, "controlled", settings)
    baseline_peak = baseline["peak_demand_kw"]
    controlled_peak = controlled["peak_demand_kw"]
    absolute = (
        float(baseline_peak - controlled_peak)
        if isinstance(baseline_peak, float)
        and isinstance(controlled_peak, float)
        else None
    )
    percentage = (
        float(absolute / baseline_peak * 100)
        if absolute is not None and baseline_peak
        else None
    )
    summary: dict[str, object] = {
        "baseline_peak_demand_kw": baseline_peak,
        "controlled_peak_demand_kw": controlled_peak,
        "absolute_peak_reduction_kw": absolute,
        "peak_reduction_percent": percentage,
        "baseline_peak_timestamp": baseline["peak_timestamp"],
        "controlled_peak_timestamp": controlled["peak_timestamp"],
        "baseline_average_demand_kw": baseline["average_demand_kw"],
        "controlled_average_demand_kw": controlled["average_demand_kw"],
        "baseline_intervals_above_warning": baseline[
            "intervals_above_warning"
        ],
        "controlled_intervals_above_warning": controlled[
            "intervals_above_warning"
        ],
        "baseline_intervals_above_critical": baseline[
            "intervals_above_critical"
        ],
        "controlled_intervals_above_critical": controlled[
            "intervals_above_critical"
        ],
        "warning_threshold_kw": settings.demand_warning_kw,
        "critical_threshold_kw": settings.demand_critical_kw,
    }
    interval = matched[[
        "timestamp",
        "facility_demand_kw_baseline",
        "facility_demand_kw_controlled",
    ]].rename(columns={
        "facility_demand_kw_baseline": "baseline_demand_kw",
        "facility_demand_kw_controlled": "controlled_demand_kw",
    })
    interval["warning_threshold_kw"] = settings.demand_warning_kw
    interval["critical_threshold_kw"] = settings.demand_critical_kw
    return summary, interval.reset_index(drop=True)


__all__ = ["calculate_demand_metrics"]
