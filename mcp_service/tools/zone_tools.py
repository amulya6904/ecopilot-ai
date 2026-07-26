"""Bounded official EnergyPlus zone tools."""

from typing import Any

from mcp_service.context import MCPApplicationContext
from mcp_service.errors import ErrorCode, MCPToolError
from mcp_service.limits import bounded_frame
from mcp_service.tools import execute_tool


def _resolve_zone(context: MCPApplicationContext, name: str) -> tuple[str, str, str]:
    target = name.strip().casefold()
    matches = [
        (technical, display, context.baseline_settings.zone_roles[technical])
        for technical, display in context.baseline_settings.zone_display_names.items()
        if target in {technical.casefold(), display.casefold()}
    ]
    if len(matches) != 1:
        qualifier = "ambiguous" if matches else "unknown"
        raise MCPToolError(ErrorCode.INVALID_ZONE, f"Zone name is {qualifier}: {name!r}.")
    return matches[0]


def list_zones(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        summary = context.load_json("summary.json")
        available = summary.get("actual_available_outputs", {})
        return {"zones": [
            {
                "energyplus_zone_name": technical,
                "display_zone_name": display,
                "role": context.baseline_settings.zone_roles[technical],
                "included_in_comfort": (
                    "occupied" in context.baseline_settings.zone_roles[technical]
                    and context.baseline_settings.zone_roles[technical] != "plenum"
                ),
                "data_availability": {
                    "temperature": bool(available.get("zone_temperature")),
                    "occupancy": bool(available.get("occupancy")),
                    "pmv": bool(available.get("pmv")),
                },
            }
            for technical, display in context.baseline_settings.zone_display_names.items()
        ]}
    return execute_tool(context, "list_zones", {}, handler)


def get_zone_summary(context: MCPApplicationContext, zone_name: str) -> dict[str, Any]:
    def handler() -> Any:
        technical, display, role = _resolve_zone(context, zone_name)
        frame = context.load_csv("zone_summary.csv")
        matches = frame[frame["energyplus_zone_name"].str.casefold() == technical.casefold()]
        if matches.empty:
            raise MCPToolError(ErrorCode.ARTIFACT_NOT_FOUND, "Zone summary is unavailable.")
        row = matches.iloc[0].to_dict()
        row["included_in_comfort"] = "occupied" in role and role != "plenum"
        row["comfort_interpretation"] = (
            "excluded_plenum" if role == "plenum" else "occupied_zone"
        )
        row["display_zone_name"] = display
        return row
    return execute_tool(context, "get_zone_summary", {"zone_name": zone_name}, handler)


def get_zone_telemetry(
    context: MCPApplicationContext,
    zone_name: str,
    *,
    start=None,
    end=None,
    aggregation: str = "raw",
    limit: int | None = None,
) -> dict[str, Any]:
    effective_limit = limit or context.settings.default_telemetry_records
    inputs = {
        "zone_name": zone_name, "start": start, "end": end,
        "aggregation": aggregation, "limit": effective_limit,
    }
    def handler() -> Any:
        technical, display, role = _resolve_zone(context, zone_name)
        frame = context.load_csv("zone_telemetry.csv")
        frame = frame[frame["energyplus_zone_name"].str.casefold() == technical.casefold()]
        bounded, info = bounded_frame(
            frame, start=start, end=end, aggregation=aggregation,
            limit=effective_limit, maximum=context.settings.max_telemetry_records,
            group_columns=("energyplus_zone_name", "display_zone_name", "zone_role"),
        )
        return {
            "energyplus_zone_name": technical,
            "display_zone_name": display,
            "role": role,
            "included_in_comfort": "occupied" in role and role != "plenum",
            "records": bounded,
            **info,
        }
    return execute_tool(context, "get_zone_telemetry", inputs, handler)


__all__ = ["get_zone_summary", "get_zone_telemetry", "list_zones"]
