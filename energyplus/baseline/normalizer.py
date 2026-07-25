"""Normalize raw EnergyPlus CSV output into zone and facility Phase 5 tables."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Mapping

import pandas as pd

from energyplus.baseline.schedule_inspector import BaselineModelInspection
from energyplus.baseline.settings import EnergyPlusBaselineSettings


ZONE_TELEMETRY_COLUMNS = (
    "timestamp",
    "energyplus_zone_name",
    "display_zone_name",
    "zone_role",
    "indoor_temperature_c",
    "cooling_setpoint_c",
    "heating_setpoint_c",
    "occupancy",
    "relative_humidity_percent",
    "pmv",
    "ppd_percent",
    "outdoor_temperature_c",
    "backend",
    "source",
    "classification",
    "official_result",
    "baseline_result",
)

FACILITY_TELEMETRY_COLUMNS = (
    "timestamp",
    "facility_electricity_kwh",
    "facility_demand_kw",
    "hvac_electricity_kwh",
    "cooling_electricity_kwh",
    "heating_electricity_kwh",
    "fan_electricity_kwh",
    "outdoor_temperature_c",
    "backend",
    "source",
    "classification",
    "official_result",
    "baseline_result",
)


@dataclass
class NormalizedBaselineTelemetry:
    zone: pd.DataFrame
    facility: pd.DataFrame
    actual_available_outputs: dict[str, bool]
    source_columns: tuple[str, ...]
    timestamp_convention: str = (
        "EnergyPlus hourly interval-end timestamps; yearless values use reference "
        "year 2000 and 24:00 rolls into the following day."
    )


_ENERGYPLUS_TIME = re.compile(
    r"^\s*(?P<month>\d{1,2})/(?P<day>\d{1,2})\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?\s*$"
)


def parse_energyplus_timestamp(value: object, reference_year: int = 2000) -> pd.Timestamp:
    """Parse EnergyPlus's yearless, hour-ending timestamps including 24:00."""
    text = str(value).strip()
    match = _ENERGYPLUS_TIME.match(text)
    if not match:
        parsed = pd.to_datetime(text, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(f"Unrecognized EnergyPlus timestamp: {value!r}")
        return pd.Timestamp(parsed)
    hour = int(match.group("hour"))
    if not 0 <= hour <= 24:
        raise ValueError(f"Invalid EnergyPlus hour: {hour}")
    minute = int(match.group("minute"))
    second = int(match.group("second") or 0)
    if hour == 24 and (minute or second):
        raise ValueError("EnergyPlus 24:00 cannot include non-zero minutes.")
    base = datetime(
        reference_year,
        int(match.group("month")),
        int(match.group("day")),
    )
    return pd.Timestamp(base + timedelta(hours=hour, minutes=minute, seconds=second))


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _find_column(columns: list[str], phrase: str, unit: str | None = None) -> str | None:
    phrase_key = _normalized(phrase)
    for column in columns:
        key = _normalized(column)
        if phrase_key in key and (unit is None or unit.casefold() in key):
            return column
    return None


def _variable_columns(columns: list[str], phrase: str) -> dict[str, list[str]]:
    phrase_key = _normalized(phrase)
    result: dict[str, list[str]] = {}
    for column in columns:
        if phrase_key not in _normalized(column) or ":" not in column:
            continue
        key = column.split(":", 1)[0].strip()
        result.setdefault(key.casefold(), []).append(column)
    return result


def _numeric(raw: pd.DataFrame, column: str | None) -> pd.Series:
    if column is None:
        return pd.Series(float("nan"), index=raw.index, dtype=float)
    return pd.to_numeric(raw[column], errors="coerce")


def _lookup(mapping: Mapping[str, str], technical_name: str, default: str) -> str:
    key = technical_name.casefold()
    return next(
        (value for name, value in mapping.items() if name.casefold() == key),
        default,
    )


def _series_for_key(
    raw: pd.DataFrame,
    mapping: dict[str, list[str]],
    key: str,
) -> pd.Series:
    columns = mapping.get(key.casefold(), [])
    if not columns:
        return pd.Series(float("nan"), index=raw.index, dtype=float)
    values = raw[columns].apply(pd.to_numeric, errors="coerce")
    return values.mean(axis=1, skipna=True)


def normalize_energyplus_baseline_csv(
    csv_path: Path,
    settings: EnergyPlusBaselineSettings,
    inspection: BaselineModelInspection | None = None,
) -> NormalizedBaselineTelemetry:
    """Create stable, non-duplicated zone and facility telemetry tables."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"EnergyPlus CSV does not exist: {path}")
    raw = pd.read_csv(path)
    if raw.empty:
        raise ValueError("EnergyPlus baseline CSV is empty.")
    columns = list(raw.columns)
    time_column = next(
        (column for column in columns if _normalized(column) == "date/time"),
        None,
    )
    if time_column is None:
        raise ValueError("EnergyPlus CSV has no Date/Time column.")
    timestamps = raw[time_column].map(parse_energyplus_timestamp)
    if timestamps.duplicated().any():
        raise ValueError("EnergyPlus CSV contains duplicate facility timestamps.")

    zone_temperature = _variable_columns(columns, "Zone Mean Air Temperature")
    if not zone_temperature:
        zone_temperature = _variable_columns(columns, "Zone Air Temperature")
    cooling_setpoint = _variable_columns(
        columns, "Zone Thermostat Cooling Setpoint Temperature"
    )
    heating_setpoint = _variable_columns(
        columns, "Zone Thermostat Heating Setpoint Temperature"
    )
    occupancy = _variable_columns(columns, "Zone People Occupant Count")
    humidity = _variable_columns(columns, "Zone Air Relative Humidity")
    pmv_raw = _variable_columns(columns, "Zone Thermal Comfort Fanger Model PMV")
    ppd_raw = _variable_columns(columns, "Zone Thermal Comfort Fanger Model PPD")
    outdoor_temperature_column = _find_column(
        columns, "Site Outdoor Air Drybulb Temperature"
    )
    outdoor_temperature = _numeric(raw, outdoor_temperature_column)

    people_to_zone: dict[str, str] = {}
    if inspection is not None:
        for reference in inspection.occupancy_references:
            if reference.referenced_zones:
                people_to_zone[reference.object_name.casefold()] = (
                    reference.referenced_zones[0]
                )

    def remap_people_columns(
        source: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        remapped: dict[str, list[str]] = {}
        for key, source_columns in source.items():
            zone = people_to_zone.get(key, key)
            remapped.setdefault(zone.casefold(), []).extend(source_columns)
        return remapped

    pmv = remap_people_columns(pmv_raw)
    ppd = remap_people_columns(ppd_raw)
    technical_names = sorted(
        (
            columns_for_zone[0].split(":", 1)[0].strip()
            for columns_for_zone in zone_temperature.values()
        ),
        key=str.casefold,
    )
    zone_frames: list[pd.DataFrame] = []
    for technical_name in technical_names:
        key = technical_name.casefold()
        zone_frames.append(pd.DataFrame({
            "timestamp": timestamps,
            "energyplus_zone_name": technical_name,
            "display_zone_name": _lookup(
                settings.zone_display_names, technical_name, technical_name
            ),
            "zone_role": _lookup(
                settings.zone_roles, technical_name, "unclassified"
            ),
            "indoor_temperature_c": _series_for_key(
                raw, zone_temperature, key
            ),
            "cooling_setpoint_c": _series_for_key(raw, cooling_setpoint, key),
            "heating_setpoint_c": _series_for_key(raw, heating_setpoint, key),
            "occupancy": _series_for_key(raw, occupancy, key),
            "relative_humidity_percent": _series_for_key(raw, humidity, key),
            "pmv": _series_for_key(raw, pmv, key),
            "ppd_percent": _series_for_key(raw, ppd, key),
            "outdoor_temperature_c": outdoor_temperature,
            "backend": "energyplus",
            "source": "EnergyPlus",
            "classification": "official_energyplus_baseline",
            "official_result": True,
            "baseline_result": True,
        }))
    zone = (
        pd.concat(zone_frames, ignore_index=True)
        if zone_frames
        else pd.DataFrame(columns=ZONE_TELEMETRY_COLUMNS)
    )
    if zone.duplicated(["timestamp", "energyplus_zone_name"]).any():
        raise ValueError("Duplicate timestamp-zone pairs in baseline telemetry.")
    zone = zone.loc[:, ZONE_TELEMETRY_COLUMNS].sort_values(
        ["timestamp", "energyplus_zone_name"],
        kind="stable",
        ignore_index=True,
    )

    energy_column = _find_column(columns, "Electricity:Facility", "[J]")
    demand_column = _find_column(
        columns, "Facility Total Electricity Demand Rate", "[W]"
    )
    hvac_column = _find_column(columns, "Electricity:HVAC", "[J]")
    cooling_column = _find_column(columns, "Cooling:Electricity", "[J]")
    heating_column = _find_column(columns, "Heating:Electricity", "[J]")
    fan_column = _find_column(columns, "Fans:Electricity", "[J]")
    facility = pd.DataFrame({
        "timestamp": timestamps,
        "facility_electricity_kwh": _numeric(raw, energy_column) / 3_600_000,
        "facility_demand_kw": _numeric(raw, demand_column) / 1000,
        "hvac_electricity_kwh": _numeric(raw, hvac_column) / 3_600_000,
        "cooling_electricity_kwh": _numeric(raw, cooling_column) / 3_600_000,
        "heating_electricity_kwh": _numeric(raw, heating_column) / 3_600_000,
        "fan_electricity_kwh": _numeric(raw, fan_column) / 3_600_000,
        "outdoor_temperature_c": outdoor_temperature,
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": "official_energyplus_baseline",
        "official_result": True,
        "baseline_result": True,
    }).loc[:, FACILITY_TELEMETRY_COLUMNS].sort_values(
        "timestamp", kind="stable", ignore_index=True
    )
    actual = {
        "zone_temperature": bool(
            not zone.empty and zone["indoor_temperature_c"].notna().any()
        ),
        "cooling_setpoint": bool(
            not zone.empty and zone["cooling_setpoint_c"].notna().any()
        ),
        "heating_setpoint": bool(
            not zone.empty and zone["heating_setpoint_c"].notna().any()
        ),
        "occupancy": bool(
            not zone.empty and zone["occupancy"].notna().any()
        ),
        "zone_relative_humidity": bool(
            not zone.empty and zone["relative_humidity_percent"].notna().any()
        ),
        "pmv": bool(not zone.empty and zone["pmv"].notna().any()),
        "ppd": bool(not zone.empty and zone["ppd_percent"].notna().any()),
        "outdoor_temperature": facility["outdoor_temperature_c"].notna().any(),
        "facility_electricity": facility["facility_electricity_kwh"].notna().any(),
        "facility_demand": facility["facility_demand_kw"].notna().any(),
        "hvac_electricity": facility["hvac_electricity_kwh"].notna().any(),
        "cooling_electricity": facility["cooling_electricity_kwh"].notna().any(),
        "heating_electricity": facility["heating_electricity_kwh"].notna().any(),
        "fan_electricity": facility["fan_electricity_kwh"].notna().any(),
    }
    zone.attrs["timestamp_convention"] = (
        "hour-ending; reference year 2000 for yearless timestamps"
    )
    facility.attrs.update(zone.attrs)
    return NormalizedBaselineTelemetry(
        zone=zone,
        facility=facility,
        actual_available_outputs={key: bool(value) for key, value in actual.items()},
        source_columns=tuple(columns),
    )


__all__ = [
    "FACILITY_TELEMETRY_COLUMNS",
    "NormalizedBaselineTelemetry",
    "ZONE_TELEMETRY_COLUMNS",
    "normalize_energyplus_baseline_csv",
    "parse_energyplus_timestamp",
]
