"""Parse separate zone-level and building-level EnergyPlus telemetry."""

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd


@dataclass(frozen=True)
class EnergyPlusTelemetrySummary:
    row_count: int
    zones: tuple[str, ...]
    zone_temperature_available: bool
    outdoor_temperature_available: bool
    electricity_available: bool
    demand_available: bool
    total_electricity_kwh: float | None
    peak_demand_kw: float | None
    electricity_source_column: str | None
    demand_source_column: str | None
    demand_calculation_method: str | None
    reporting_frequency: str | None
    reporting_interval_minutes: int | None
    pmv_available: bool = False
    co2_available: bool = False
    backend: str = "energyplus"
    source: str = "EnergyPlus"
    classification: str = "official_energyplus_simulation"
    official_result: bool = True
    ai_controlled: bool = False
    closed_loop: bool = False
    optimized: bool = False
    savings_result: bool = False


@dataclass
class EnergyPlusTelemetry:
    zone: pd.DataFrame
    building: pd.DataFrame
    summary: EnergyPlusTelemetrySummary


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _find(columns: list[str], phrase: str, unit: str | None = None) -> str | None:
    phrase_key = _normalized(phrase)
    for column in columns:
        key = _normalized(column)
        if phrase_key in key and (unit is None or unit.casefold() in key):
            return column
    return None


def _find_all(columns: list[str], *phrases: str) -> list[str]:
    phrase_keys = tuple(_normalized(phrase) for phrase in phrases)
    return [
        column
        for column in columns
        if any(phrase in _normalized(column) for phrase in phrase_keys)
    ]


def _frequency(column: str | None) -> tuple[str | None, int | None]:
    if column is None:
        return None, None
    match = re.search(r"\((Hourly|Timestep|Daily|Monthly|RunPeriod)\)\s*$", column, re.I)
    if not match:
        return None, None
    frequency = match.group(1).title()
    return frequency, 60 if frequency == "Hourly" else None


def parse_energyplus_outputs(path: Path) -> EnergyPlusTelemetry:
    """Parse one EnergyPlus CSV into independent zone and building tables."""
    csv_path = Path(path)
    raw = pd.read_csv(csv_path)
    if raw.empty:
        raise ValueError("EnergyPlus CSV is empty.")
    columns = list(raw.columns)
    time_column = next(
        (column for column in columns if _normalized(column) == "date/time"),
        None,
    )
    timestamp = (
        raw[time_column].astype(str).str.strip()
        if time_column else pd.Series(range(len(raw)), name="timestamp")
    )
    zone_columns = _find_all(columns, "Zone Mean Air Temperature")
    if not zone_columns:
        zone_columns = _find_all(columns, "Zone Air Temperature")
    outdoor_column = _find(columns, "Site Outdoor Air Drybulb Temperature")
    electricity_column = _find(columns, "Electricity:Facility", "[j]")
    demand_column = _find(
        columns, "Facility Total Electricity Demand Rate", "[w]"
    )
    zone_frames: list[pd.DataFrame] = []
    for column in zone_columns:
        zone_frames.append(pd.DataFrame({
            "timestamp": timestamp,
            "zone_name": column.split(":", 1)[0].strip(),
            "indoor_temperature_c": pd.to_numeric(raw[column], errors="coerce"),
            "outdoor_temperature_c": (
                pd.to_numeric(raw[outdoor_column], errors="coerce")
                if outdoor_column else None
            ),
        }))
    zone = (
        pd.concat(zone_frames, ignore_index=True)
        if zone_frames
        else pd.DataFrame(columns=[
            "timestamp", "zone_name", "indoor_temperature_c",
            "outdoor_temperature_c",
        ])
    )
    building = pd.DataFrame({"timestamp": timestamp})
    building["outdoor_temperature_c"] = (
        pd.to_numeric(raw[outdoor_column], errors="coerce")
        if outdoor_column else None
    )
    building["interval_electricity_kwh"] = (
        pd.to_numeric(raw[electricity_column], errors="coerce") / 3_600_000
        if electricity_column else None
    )
    reporting_frequency, interval_minutes = _frequency(
        demand_column or electricity_column
    )
    demand_method = None
    if demand_column:
        building["facility_demand_kw"] = (
            pd.to_numeric(raw[demand_column], errors="coerce") / 1000
        )
        demand_method = "direct"
    elif electricity_column and interval_minutes:
        building["facility_demand_kw"] = (
            building["interval_electricity_kwh"] / (interval_minutes / 60)
        )
        demand_method = "derived"
    else:
        building["facility_demand_kw"] = None
    metadata = {
        "source_columns": tuple(columns),
        "electricity_source_column": electricity_column,
        "demand_source_column": demand_column or electricity_column,
        "demand_calculation_method": demand_method,
        "reporting_frequency": reporting_frequency,
        "reporting_interval_minutes": interval_minutes,
    }
    zone.attrs.update(metadata)
    building.attrs.update(metadata)
    for frame in (zone, building):
        frame["backend"] = "energyplus"
        frame["source"] = "EnergyPlus"
        frame["classification"] = "official_energyplus_simulation"
        frame["official_result"] = True
    summary = summarize_energyplus_telemetry(zone, building)
    return EnergyPlusTelemetry(zone=zone, building=building, summary=summary)


def parse_energyplus_csv(path: Path) -> pd.DataFrame:
    """Backward-compatible zone telemetry parser."""
    telemetry = parse_energyplus_outputs(path)
    telemetry.zone.attrs["building_telemetry"] = telemetry.building
    return telemetry.zone


def summarize_energyplus_telemetry(
    zone: pd.DataFrame,
    building: pd.DataFrame | None = None,
) -> EnergyPlusTelemetrySummary:
    """Summarize building values exactly once per EnergyPlus timestamp."""
    building = building if building is not None else zone.attrs.get(
        "building_telemetry", pd.DataFrame()
    )
    zones = tuple(sorted(zone["zone_name"].dropna().astype(str).unique()))
    energy = (
        pd.to_numeric(building["interval_electricity_kwh"], errors="coerce").dropna()
        if "interval_electricity_kwh" in building else pd.Series(dtype=float)
    )
    demand = (
        pd.to_numeric(building["facility_demand_kw"], errors="coerce").dropna()
        if "facility_demand_kw" in building else pd.Series(dtype=float)
    )
    attrs = building.attrs or zone.attrs
    return EnergyPlusTelemetrySummary(
        row_count=len(zone),
        zones=zones,
        zone_temperature_available=bool(
            "indoor_temperature_c" in zone
            and zone["indoor_temperature_c"].notna().any()
        ),
        outdoor_temperature_available=bool(
            (
                "outdoor_temperature_c" in building
                and building["outdoor_temperature_c"].notna().any()
            )
            or (
                "outdoor_temperature_c" in zone
                and zone["outdoor_temperature_c"].notna().any()
            )
        ),
        electricity_available=not energy.empty,
        demand_available=not demand.empty,
        total_electricity_kwh=float(energy.sum()) if not energy.empty else None,
        peak_demand_kw=float(demand.max()) if not demand.empty else None,
        electricity_source_column=attrs.get("electricity_source_column"),
        demand_source_column=attrs.get("demand_source_column"),
        demand_calculation_method=attrs.get("demand_calculation_method"),
        reporting_frequency=attrs.get("reporting_frequency"),
        reporting_interval_minutes=attrs.get("reporting_interval_minutes"),
    )
