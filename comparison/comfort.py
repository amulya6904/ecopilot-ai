"""Occupied-zone temperature proxy and genuine-PMV comfort metrics."""

import pandas as pd

from .schemas import ComfortMetrics
from .settings import COMPARISON_SETTINGS, ComparisonSettings


def _conditioned(role: object) -> bool:
    value = str(role).casefold()
    return "occupied" in value and "plenum" not in value


def _interval_hours(frame: pd.DataFrame) -> pd.Series:
    ordered = frame.sort_values(
        ["energyplus_zone_name", "timestamp"], kind="stable"
    )
    differences = ordered.groupby("energyplus_zone_name")[
        "timestamp"
    ].diff().dt.total_seconds().div(3600)
    typical = differences[differences > 0].median()
    fill = float(typical) if pd.notna(typical) else 1.0
    result = differences.where(differences > 0, fill).fillna(fill)
    return result.reindex(frame.index)


def _calculate_side(
    aligned_zone: pd.DataFrame,
    suffix: str,
    settings: ComparisonSettings,
) -> ComfortMetrics:
    matched = aligned_zone.loc[aligned_zone["_merge"] == "both"].copy()
    role = matched[f"zone_role_{suffix}"]
    occupancy = pd.to_numeric(
        matched[f"occupancy_{suffix}"], errors="coerce"
    )
    temperature = pd.to_numeric(
        matched[f"indoor_temperature_c_{suffix}"], errors="coerce"
    )
    occupied = (
        role.map(_conditioned)
        & occupancy.fillna(0).gt(0)
        & temperature.notna()
    )
    values = temperature.loc[occupied]
    compliant = values.between(
        settings.occupied_temperature_min_c,
        settings.occupied_temperature_max_c,
        inclusive="both",
    )
    low_deviation = (
        settings.occupied_temperature_min_c - values
    ).clip(lower=0)
    high_deviation = (
        values - settings.occupied_temperature_max_c
    ).clip(lower=0)
    deviation = pd.concat(
        [low_deviation, high_deviation], axis=1
    ).max(axis=1)
    hours = _interval_hours(matched).loc[occupied]
    pmv = pd.to_numeric(matched[f"pmv_{suffix}"], errors="coerce")
    ppd = pd.to_numeric(
        matched[f"ppd_percent_{suffix}"], errors="coerce"
    )
    pmv_records = occupied & pmv.notna()
    genuine_pmv = pmv.loc[pmv_records]
    pmv_compliant = genuine_pmv.between(
        settings.pmv_min, settings.pmv_max, inclusive="both"
    )
    genuine_ppd = ppd.loc[pmv_records & ppd.notna()]
    count = int(len(values))
    return ComfortMetrics(
        occupied_records=count,
        temperature_compliant_records=int(compliant.sum()),
        temperature_compliance_percent=(
            float(compliant.mean() * 100) if count else None
        ),
        low_temperature_violations=int(
            (values < settings.occupied_temperature_min_c).sum()
        ),
        high_temperature_violations=int(
            (values > settings.occupied_temperature_max_c).sum()
        ),
        maximum_deviation_c=(
            float(deviation.max()) if not deviation.empty else None
        ),
        average_occupied_temperature_c=(
            float(values.mean()) if not values.empty else None
        ),
        degree_hours_outside_comfort=(
            float((deviation * hours).sum()) if not deviation.empty else 0.0
        ),
        pmv_available=bool(not genuine_pmv.empty),
        pmv_compliance_percent=(
            float(pmv_compliant.mean() * 100)
            if not genuine_pmv.empty
            else None
        ),
        average_pmv=(
            float(genuine_pmv.mean()) if not genuine_pmv.empty else None
        ),
        maximum_absolute_pmv=(
            float(genuine_pmv.abs().max()) if not genuine_pmv.empty else None
        ),
        average_ppd_percent=(
            float(genuine_ppd.mean()) if not genuine_ppd.empty else None
        ),
        maximum_ppd_percent=(
            float(genuine_ppd.max()) if not genuine_ppd.empty else None
        ),
        comfort_method=(
            "pmv_ppd"
            if not genuine_pmv.empty
            else "occupied_temperature_proxy"
        ),
    )


def calculate_comfort_metrics(
    aligned_zone: pd.DataFrame,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> tuple[ComfortMetrics, ComfortMetrics, dict[str, object], pd.DataFrame]:
    baseline = _calculate_side(aligned_zone, "baseline", settings)
    controlled = _calculate_side(aligned_zone, "controlled", settings)
    baseline_percent = baseline.temperature_compliance_percent
    controlled_percent = controlled.temperature_compliance_percent
    change = (
        float(controlled_percent - baseline_percent)
        if baseline_percent is not None and controlled_percent is not None
        else None
    )
    degradation = max(0.0, -change) if change is not None else None
    gate = bool(
        controlled_percent is not None
        and controlled_percent + settings.comfort_tolerance_percent
        >= settings.minimum_comfort_compliance_percent
        and degradation is not None
        and degradation
        <= (
            settings.maximum_allowed_comfort_degradation_percent
            + settings.comfort_tolerance_percent
        )
    )
    summary: dict[str, object] = {
        "baseline": baseline.model_dump(mode="json"),
        "controlled": controlled.model_dump(mode="json"),
        "comfort_change_percent_points": change,
        "comfort_degradation_percent_points": degradation,
        "minimum_comfort_compliance_percent": (
            settings.minimum_comfort_compliance_percent
        ),
        "maximum_allowed_comfort_degradation_percent": (
            settings.maximum_allowed_comfort_degradation_percent
        ),
        "comfort_gate_passed": gate,
    }
    matched = aligned_zone.loc[
        aligned_zone["_merge"] == "both"
    ].copy()
    columns = [
        "timestamp",
        "energyplus_zone_name",
        "occupancy_baseline",
        "occupancy_controlled",
        "indoor_temperature_c_baseline",
        "indoor_temperature_c_controlled",
        "cooling_setpoint_c_baseline",
        "cooling_setpoint_c_controlled",
        "pmv_baseline",
        "pmv_controlled",
        "ppd_percent_baseline",
        "ppd_percent_controlled",
    ]
    comparison = matched.loc[:, columns]
    comparison["comfort_min_c"] = settings.occupied_temperature_min_c
    comparison["comfort_max_c"] = settings.occupied_temperature_max_c
    return baseline, controlled, summary, comparison.reset_index(drop=True)


__all__ = ["calculate_comfort_metrics"]
