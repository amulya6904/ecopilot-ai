"""Stable Phase 10 facility, zone, and action table normalization."""

from typing import Any

import pandas as pd


FACILITY_COLUMNS = (
    "timestamp",
    "facility_electricity_kwh",
    "facility_demand_kw",
    "hvac_electricity_kwh",
    "cooling_electricity_kwh",
    "heating_electricity_kwh",
    "fan_electricity_kwh",
    "outdoor_temperature_c",
    "source_run",
    "classification",
)

ZONE_COLUMNS = (
    "timestamp",
    "energyplus_zone_name",
    "display_zone_name",
    "zone_role",
    "occupancy",
    "indoor_temperature_c",
    "cooling_setpoint_c",
    "heating_setpoint_c",
    "relative_humidity_percent",
    "pmv",
    "ppd_percent",
    "comfort_method",
    "source_run",
)

ACTION_COLUMNS = (
    "timestamp",
    "proposal_id",
    "action_id",
    "requested_setpoint_c",
    "approved_setpoint_c",
    "applied_setpoint_c",
    "observed_setpoint_c",
    "decision",
    "safety_level",
    "fallback",
    "rollback",
)


def _timestamps(frame: pd.DataFrame) -> pd.Series:
    values = pd.to_datetime(frame["timestamp"], errors="coerce")
    if values.isna().any():
        raise ValueError("Telemetry contains invalid timestamps.")
    if getattr(values.dt, "tz", None) is not None:
        values = values.dt.tz_convert(None)
    return values


def _numeric_or_null(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(float("nan"), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def normalize_facility(
    frame: pd.DataFrame, *, run_id: str, classification: str
) -> pd.DataFrame:
    """Normalize one facility row per interval; never join facility data to zones."""

    if frame.empty:
        raise ValueError("Facility telemetry is empty.")
    source_energy = (
        "facility_electricity_kwh"
        if "facility_electricity_kwh" in frame
        else "interval_electricity_kwh"
    )
    normalized = pd.DataFrame({
        "timestamp": _timestamps(frame),
        "facility_electricity_kwh": _numeric_or_null(frame, source_energy),
        "facility_demand_kw": _numeric_or_null(frame, "facility_demand_kw"),
        "hvac_electricity_kwh": _numeric_or_null(
            frame, "hvac_electricity_kwh"
        ),
        "cooling_electricity_kwh": _numeric_or_null(
            frame, "cooling_electricity_kwh"
        ),
        "heating_electricity_kwh": _numeric_or_null(
            frame, "heating_electricity_kwh"
        ),
        "fan_electricity_kwh": _numeric_or_null(
            frame, "fan_electricity_kwh"
        ),
        "outdoor_temperature_c": _numeric_or_null(
            frame, "outdoor_temperature_c"
        ),
        "source_run": run_id,
        "classification": classification,
    })
    if normalized["timestamp"].duplicated().any():
        raise ValueError("Facility telemetry contains duplicate intervals.")
    return normalized.loc[:, FACILITY_COLUMNS].sort_values(
        "timestamp", kind="stable", ignore_index=True
    )


def normalize_zone(frame: pd.DataFrame, *, run_id: str) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("Zone telemetry is empty.")
    required = {
        "timestamp",
        "energyplus_zone_name",
        "display_zone_name",
        "zone_role",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Zone telemetry is missing columns: " + ", ".join(sorted(missing))
        )
    pmv = _numeric_or_null(frame, "pmv")
    normalized = pd.DataFrame({
        "timestamp": _timestamps(frame),
        "energyplus_zone_name": frame["energyplus_zone_name"].astype(str),
        "display_zone_name": frame["display_zone_name"].astype(str),
        "zone_role": frame["zone_role"].astype(str),
        "occupancy": _numeric_or_null(frame, "occupancy"),
        "indoor_temperature_c": _numeric_or_null(
            frame, "indoor_temperature_c"
        ),
        "cooling_setpoint_c": _numeric_or_null(frame, "cooling_setpoint_c"),
        "heating_setpoint_c": _numeric_or_null(frame, "heating_setpoint_c"),
        "relative_humidity_percent": _numeric_or_null(
            frame, "relative_humidity_percent"
        ),
        "pmv": pmv,
        "ppd_percent": _numeric_or_null(frame, "ppd_percent"),
        "comfort_method": (
            "pmv_ppd" if pmv.notna().any() else "occupied_temperature_proxy"
        ),
        "source_run": run_id,
    })
    if normalized.duplicated(
        ["timestamp", "energyplus_zone_name"]
    ).any():
        raise ValueError("Zone telemetry contains duplicate timestamp-zone pairs.")
    return normalized.loc[:, ZONE_COLUMNS].sort_values(
        ["timestamp", "energyplus_zone_name"],
        kind="stable",
        ignore_index=True,
    )


def normalize_actions(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=ACTION_COLUMNS)
    timestamp_source = (
        "timestamp" if "timestamp" in frame else "simulation_timestamp"
    )
    aliases: dict[str, tuple[str, ...]] = {
        "proposal_id": ("proposal_id", "source_proposal_id"),
        "action_id": ("action_id",),
        "requested_setpoint_c": (
            "requested_setpoint_c",
            "requested_value",
            "requested_value_c",
        ),
        "approved_setpoint_c": (
            "approved_setpoint_c",
            "approved_value",
            "approved_value_c",
        ),
        "applied_setpoint_c": (
            "applied_setpoint_c",
            "applied_value",
        ),
        "observed_setpoint_c": (
            "observed_setpoint_c",
            "observed_setpoint_after_application",
        ),
        "decision": ("decision", "outcome"),
        "safety_level": ("safety_level",),
        "fallback": ("fallback", "fallback_required"),
        "rollback": ("rollback", "rollback_required"),
    }

    def first(names: tuple[str, ...], default: Any = None) -> pd.Series:
        for name in names:
            if name in frame:
                return frame[name]
        return pd.Series(default, index=frame.index)

    normalized = pd.DataFrame({
        "timestamp": pd.to_datetime(
            frame[timestamp_source], errors="coerce"
        ),
        **{key: first(names) for key, names in aliases.items()},
    })
    if normalized["timestamp"].isna().any():
        raise ValueError("Action telemetry contains invalid timestamps.")
    for column in (
        "requested_setpoint_c",
        "approved_setpoint_c",
        "applied_setpoint_c",
        "observed_setpoint_c",
    ):
        normalized[column] = pd.to_numeric(
            normalized[column], errors="coerce"
        )
    normalized["fallback"] = normalized["fallback"].fillna(False).astype(bool)
    normalized["rollback"] = normalized["rollback"].fillna(False).astype(bool)
    return normalized.loc[:, ACTION_COLUMNS].sort_values(
        "timestamp", kind="stable", ignore_index=True
    )


__all__ = [
    "ACTION_COLUMNS",
    "FACILITY_COLUMNS",
    "ZONE_COLUMNS",
    "normalize_actions",
    "normalize_facility",
    "normalize_zone",
]
