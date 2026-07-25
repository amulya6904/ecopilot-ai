"""Official Phase 5 energy, demand, comfort, and schedule metrics."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from energyplus.baseline.normalizer import NormalizedBaselineTelemetry
from energyplus.baseline.settings import EnergyPlusBaselineSettings


@dataclass
class BaselineMetrics:
    summary: dict[str, Any]
    zone_summary: pd.DataFrame
    schedule_boundary_table: pd.DataFrame


def _number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, int):
        return int(value)
    return float(value)


def _optional_sum(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.sum()) if not values.empty else None


def _is_conditioned_role(value: object) -> bool:
    role = str(value).casefold()
    return role not in {"plenum", "non_occupied", "unclassified"} and (
        "occupied" in role
    )


def _expected_schedule_value(
    timestamp: pd.Timestamp,
    *,
    occupied_start: int,
    occupied_end: int,
    occupied_value: float,
    unoccupied_value: float,
) -> float:
    """Return the value for an EnergyPlus hourly interval-end timestamp."""
    hour = timestamp.hour
    occupied_interval = occupied_start < hour <= occupied_end
    return occupied_value if occupied_interval else unoccupied_value


def _occupied_mask(
    zone: pd.DataFrame,
    settings: EnergyPlusBaselineSettings,
) -> tuple[pd.Series, bool, str]:
    occupancy_available = (
        "occupancy" in zone and zone["occupancy"].notna().any()
    )
    if occupancy_available:
        occupied = pd.to_numeric(zone["occupancy"], errors="coerce").fillna(0) > 0
        return occupied, True, "energyplus_people_output"
    occupied = zone["timestamp"].map(
        lambda value: (
            settings.occupied_start_hour
            < pd.Timestamp(value).hour
            <= settings.occupied_end_hour
        )
    )
    return occupied.astype(bool), False, "schedule_proxy"


def _schedule_adherence(
    zone: pd.DataFrame,
    settings: EnergyPlusBaselineSettings,
) -> tuple[dict[str, Any], pd.DataFrame, pd.Series]:
    observed = pd.to_numeric(zone["cooling_setpoint_c"], errors="coerce")
    conditioned = zone["zone_role"].map(_is_conditioned_role)
    available = observed.notna() & conditioned
    expected = zone["timestamp"].map(
        lambda value: _expected_schedule_value(
            pd.Timestamp(value),
            occupied_start=settings.occupied_start_hour,
            occupied_end=settings.occupied_end_hour,
            occupied_value=settings.occupied_cooling_setpoint_c,
            unoccupied_value=settings.unoccupied_cooling_setpoint_c,
        )
    ).astype(float)
    matches = available & (
        (observed - expected).abs() <= settings.thermostat_tolerance_c
    )
    matching_count = int(matches.sum())
    available_count = int(available.sum())
    adherence = (
        matching_count / available_count * 100 if available_count else None
    )
    target_hours = {
        max(0, settings.occupied_start_hour - 1): "before_occupied_start",
        settings.occupied_start_hour: "occupied_start_hour_ending",
        (settings.occupied_start_hour + settings.occupied_end_hour) // 2:
            "middle_occupied_period",
        settings.occupied_end_hour: "occupied_end_hour_ending",
        min(23, settings.occupied_end_hour + 1): "after_occupied_end",
    }
    boundary_mask = zone["timestamp"].map(
        lambda value: pd.Timestamp(value).hour in target_hours
    )
    boundary = zone.loc[
        boundary_mask & available,
        ["timestamp", "energyplus_zone_name", "display_zone_name"],
    ].copy()
    boundary["boundary"] = boundary["timestamp"].map(
        lambda value: target_hours[pd.Timestamp(value).hour]
    )
    boundary["observed_cooling_setpoint_c"] = observed.loc[boundary.index]
    boundary["expected_cooling_setpoint_c"] = expected.loc[boundary.index]
    boundary["matches"] = matches.loc[boundary.index]
    boundary = boundary.reset_index(drop=True)
    return {
        "thermostat_output_available": bool(available_count),
        "schedule_boundary_samples": len(boundary),
        "matching_records": matching_count,
        "mismatching_records": available_count - matching_count,
        "thermostat_adherence_percent": adherence,
    }, boundary, matches


def calculate_baseline_metrics(
    telemetry: NormalizedBaselineTelemetry,
    settings: EnergyPlusBaselineSettings,
) -> BaselineMetrics:
    """Calculate official values without duplicating facility metrics by zone."""
    zone = telemetry.zone.copy()
    facility = telemetry.facility.copy()
    if zone.empty:
        raise ValueError("Zone telemetry is empty.")
    if facility.empty:
        raise ValueError("Facility telemetry is empty.")
    occupied, occupancy_available, occupancy_source = _occupied_mask(zone, settings)
    conditioned = zone["zone_role"].map(_is_conditioned_role)
    occupied_conditioned = occupied & conditioned
    temperature = pd.to_numeric(zone["indoor_temperature_c"], errors="coerce")
    temperature_records = occupied_conditioned & temperature.notna()
    temperature_compliant = temperature_records & temperature.between(
        settings.occupied_temperature_min_c,
        settings.occupied_temperature_max_c,
        inclusive="both",
    )
    low = temperature_records & (
        temperature < settings.occupied_temperature_min_c
    )
    high = temperature_records & (
        temperature > settings.occupied_temperature_max_c
    )
    occupied_temperatures = temperature.loc[temperature_records]
    deviations = pd.concat(
        (
            (
                settings.occupied_temperature_min_c - occupied_temperatures
            ).clip(lower=0),
            (
                occupied_temperatures - settings.occupied_temperature_max_c
            ).clip(lower=0),
        ),
        axis=1,
    ).max(axis=1)
    occupied_count = int(temperature_records.sum())
    temperature_compliant_count = int(temperature_compliant.sum())
    temperature_compliance = (
        temperature_compliant_count / occupied_count * 100
        if occupied_count else None
    )

    pmv = pd.to_numeric(zone["pmv"], errors="coerce")
    pmv_records = occupied_conditioned & pmv.notna()
    pmv_available = bool(pmv_records.any())
    pmv_compliant = pmv_records & pmv.between(
        settings.pmv_min, settings.pmv_max, inclusive="both"
    )
    pmv_count = int(pmv_records.sum())
    pmv_compliant_count = int(pmv_compliant.sum())
    pmv_compliance = (
        pmv_compliant_count / pmv_count * 100 if pmv_count else None
    )
    occupied_pmv = pmv.loc[pmv_records]
    ppd = pd.to_numeric(zone["ppd_percent"], errors="coerce")
    occupied_ppd = ppd.loc[pmv_records & ppd.notna()]
    adherence, boundary, thermostat_matches = _schedule_adherence(zone, settings)

    demand = pd.to_numeric(facility["facility_demand_kw"], errors="coerce")
    demand_valid = demand.dropna()
    peak_index = demand.idxmax() if not demand_valid.empty else None
    peak_timestamp = (
        pd.Timestamp(facility.loc[peak_index, "timestamp"]).isoformat()
        if peak_index is not None else None
    )
    facility_energy = _optional_sum(facility, "facility_electricity_kwh")

    summary: dict[str, Any] = {
        "total_facility_electricity_kwh": facility_energy,
        "total_hvac_electricity_kwh": _optional_sum(
            facility, "hvac_electricity_kwh"
        ),
        "total_cooling_electricity_kwh": _optional_sum(
            facility, "cooling_electricity_kwh"
        ),
        "total_heating_electricity_kwh": _optional_sum(
            facility, "heating_electricity_kwh"
        ),
        "total_fan_electricity_kwh": _optional_sum(
            facility, "fan_electricity_kwh"
        ),
        "average_facility_demand_kw": (
            float(demand_valid.mean()) if not demand_valid.empty else None
        ),
        "peak_facility_demand_kw": (
            float(demand_valid.max()) if not demand_valid.empty else None
        ),
        "peak_demand_timestamp": peak_timestamp,
        "reporting_interval_count": len(facility),
        "facility_row_count": len(facility),
        "zone_row_count": len(zone),
        "occupancy_available": occupancy_available,
        "occupancy_source": occupancy_source,
        "total_occupied_conditioned_records": occupied_count,
        "temperature_compliant_records": temperature_compliant_count,
        "temperature_compliance_percent": temperature_compliance,
        "temperature_violation_count": occupied_count - temperature_compliant_count,
        "low_temperature_violation_count": int(low.sum()),
        "high_temperature_violation_count": int(high.sum()),
        "minimum_occupied_temperature_c": _number(
            occupied_temperatures.min() if not occupied_temperatures.empty else None
        ),
        "maximum_occupied_temperature_c": _number(
            occupied_temperatures.max() if not occupied_temperatures.empty else None
        ),
        "average_occupied_temperature_c": _number(
            occupied_temperatures.mean() if not occupied_temperatures.empty else None
        ),
        "maximum_temperature_deviation_c": _number(
            deviations.max() if not deviations.empty else None
        ),
        "pmv_available": pmv_available,
        "pmv_unavailable_reason": (
            None
            if pmv_available
            else "The retained People objects do not expose Fanger PMV/PPD output."
        ),
        "total_occupied_pmv_records": pmv_count,
        "average_occupied_pmv": _number(
            occupied_pmv.mean() if not occupied_pmv.empty else None
        ),
        "minimum_occupied_pmv": _number(
            occupied_pmv.min() if not occupied_pmv.empty else None
        ),
        "maximum_occupied_pmv": _number(
            occupied_pmv.max() if not occupied_pmv.empty else None
        ),
        "pmv_compliant_records": pmv_compliant_count if pmv_available else None,
        "pmv_compliance_percent": pmv_compliance,
        "pmv_violation_count": (
            pmv_count - pmv_compliant_count if pmv_available else None
        ),
        "average_occupied_ppd_percent": _number(
            occupied_ppd.mean() if not occupied_ppd.empty else None
        ),
        **adherence,
    }

    zone_rows: list[dict[str, Any]] = []
    configured_order = {
        name.casefold(): index
        for index, name in enumerate(settings.zone_display_names)
    }
    for technical_name, group in zone.groupby(
        "energyplus_zone_name", sort=False, dropna=False
    ):
        index = group.index
        role = str(group["zone_role"].iloc[0])
        included = _is_conditioned_role(role)
        group_occupied = occupied.loc[index] & included
        group_temperature = temperature.loc[index]
        group_temperature_records = group_occupied & group_temperature.notna()
        group_compliant = group_temperature_records & group_temperature.between(
            settings.occupied_temperature_min_c,
            settings.occupied_temperature_max_c,
            inclusive="both",
        )
        group_pmv = pmv.loc[index]
        group_pmv_records = group_occupied & group_pmv.notna()
        group_pmv_compliant = group_pmv_records & group_pmv.between(
            settings.pmv_min, settings.pmv_max, inclusive="both"
        )
        group_ppd = ppd.loc[index]
        group_thermostat_available = group["cooling_setpoint_c"].notna()
        group_match = thermostat_matches.loc[index]
        occupied_records = int(group_temperature_records.sum())
        group_pmv_count = int(group_pmv_records.sum())
        available_thermostat_count = int(group_thermostat_available.sum())
        zone_rows.append({
            "energyplus_zone_name": technical_name,
            "display_zone_name": group["display_zone_name"].iloc[0],
            "zone_role": role,
            "occupied_records": occupied_records,
            "occupancy_source": occupancy_source if included else "not_applicable",
            "average_temperature_c": _number(group_temperature.mean()),
            "minimum_temperature_c": _number(group_temperature.min()),
            "maximum_temperature_c": _number(group_temperature.max()),
            "temperature_compliance_percent": (
                int(group_compliant.sum()) / occupied_records * 100
                if occupied_records else None
            ),
            "low_temperature_violations": int(
                (
                    group_temperature_records
                    & (
                        group_temperature
                        < settings.occupied_temperature_min_c
                    )
                ).sum()
            ),
            "high_temperature_violations": int(
                (
                    group_temperature_records
                    & (
                        group_temperature
                        > settings.occupied_temperature_max_c
                    )
                ).sum()
            ),
            "cooling_setpoint_available": bool(available_thermostat_count),
            "thermostat_adherence_percent": (
                int(group_match.sum()) / available_thermostat_count * 100
                if available_thermostat_count else None
            ),
            "pmv_available": bool(group_pmv_count),
            "average_pmv": _number(
                group_pmv.loc[group_pmv_records].mean()
                if group_pmv_count else None
            ),
            "pmv_compliance_percent": (
                int(group_pmv_compliant.sum()) / group_pmv_count * 100
                if group_pmv_count else None
            ),
            "average_ppd_percent": _number(
                group_ppd.loc[group_pmv_records & group_ppd.notna()].mean()
                if (group_pmv_records & group_ppd.notna()).any() else None
            ),
            "_order": configured_order.get(str(technical_name).casefold(), 10_000),
        })
    zone_summary = pd.DataFrame(zone_rows).sort_values(
        ["_order", "energyplus_zone_name"], kind="stable"
    ).drop(columns="_order").reset_index(drop=True)
    return BaselineMetrics(
        summary=summary,
        zone_summary=zone_summary,
        schedule_boundary_table=boundary,
    )


__all__ = [
    "BaselineMetrics",
    "calculate_baseline_metrics",
]
