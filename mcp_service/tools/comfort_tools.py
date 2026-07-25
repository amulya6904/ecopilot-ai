"""Temperature comfort and frozen thermostat-policy tools."""

from typing import Any

import pandas as pd

from mcp_service.context import MCPApplicationContext
from mcp_service.tools import execute_tool


def get_comfort_summary(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        summary = context.load_json("summary.json")
        keys = (
            "total_occupied_conditioned_records", "occupancy_source",
            "temperature_compliant_records", "temperature_compliance_percent",
            "temperature_violation_count", "low_temperature_violation_count",
            "high_temperature_violation_count", "minimum_occupied_temperature_c",
            "maximum_occupied_temperature_c", "pmv_available",
            "pmv_unavailable_reason", "minimum_occupied_pmv",
            "maximum_occupied_pmv", "pmv_compliance_percent",
            "average_occupied_ppd_percent",
        )
        return {
            "comfort_range_c": [
                context.baseline_settings.occupied_temperature_min_c,
                context.baseline_settings.occupied_temperature_max_c,
            ],
            "pmv_range": [context.baseline_settings.pmv_min, context.baseline_settings.pmv_max],
            "excluded_roles": ["plenum"],
            **{key: summary.get(key) for key in keys},
        }
    return execute_tool(context, "get_comfort_summary", {}, handler)


def get_thermostat_adherence(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        summary = context.load_json("summary.json")
        frame = context.load_csv("zone_telemetry.csv")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame = frame[frame["zone_role"].str.casefold() != "plenum"].copy()
        hours = frame["timestamp"].dt.hour
        expected = hours.map(
            lambda hour: context.baseline_settings.occupied_cooling_setpoint_c
            if context.baseline_settings.occupied_start_hour < hour <= context.baseline_settings.occupied_end_hour
            else context.baseline_settings.unoccupied_cooling_setpoint_c
        )
        samples = frame.loc[
            hours.isin([context.baseline_settings.occupied_start_hour,
                        context.baseline_settings.occupied_end_hour]),
            ["timestamp", "energyplus_zone_name", "display_zone_name", "cooling_setpoint_c"],
        ].head(20).copy()
        samples["expected_cooling_setpoint_c"] = expected.loc[samples.index]
        samples["matches"] = (
            samples["cooling_setpoint_c"] - samples["expected_cooling_setpoint_c"]
        ).abs() <= context.baseline_settings.thermostat_tolerance_c
        return {
            "frozen_policy": {
                "occupied_hours": [
                    context.baseline_settings.occupied_start_hour,
                    context.baseline_settings.occupied_end_hour,
                ],
                "cooling_setpoint_c": {
                    "occupied": context.baseline_settings.occupied_cooling_setpoint_c,
                    "unoccupied": context.baseline_settings.unoccupied_cooling_setpoint_c,
                },
                "heating_setpoint_c": {
                    "occupied": context.baseline_settings.occupied_heating_setpoint_c,
                    "unoccupied": context.baseline_settings.unoccupied_heating_setpoint_c,
                },
            },
            "adherence_percent": summary.get("thermostat_adherence_percent"),
            "mismatch_count": summary.get("mismatching_records"),
            "boundary_samples": samples,
            "boundary_samples_truncated": True,
        }
    return execute_tool(context, "get_thermostat_adherence", {}, handler)


__all__ = ["get_comfort_summary", "get_thermostat_adherence"]
