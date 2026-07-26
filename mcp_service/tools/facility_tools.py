"""Facility-level baseline metrics and non-duplicated telemetry."""

from typing import Any

from mcp_service.context import MCPApplicationContext
from mcp_service.limits import bounded_frame
from mcp_service.tools import execute_tool


def get_facility_summary(context: MCPApplicationContext) -> dict[str, Any]:
    keys = (
        "total_facility_electricity_kwh", "total_hvac_electricity_kwh",
        "total_cooling_electricity_kwh", "total_heating_electricity_kwh",
        "total_fan_electricity_kwh", "average_facility_demand_kw",
        "peak_facility_demand_kw", "peak_demand_timestamp",
        "reporting_interval_count",
    )
    return execute_tool(
        context, "get_facility_summary", {},
        lambda: {key: context.load_json("summary.json").get(key) for key in keys},
    )


def get_facility_telemetry(
    context: MCPApplicationContext,
    *,
    start=None,
    end=None,
    aggregation: str = "raw",
    limit: int | None = None,
) -> dict[str, Any]:
    effective_limit = limit or context.settings.default_telemetry_records
    inputs = {"start": start, "end": end, "aggregation": aggregation, "limit": effective_limit}
    def handler() -> Any:
        frame = context.load_csv("facility_telemetry.csv")
        wanted = [
            column for column in (
                "timestamp", "interval_electricity_kwh", "facility_demand_kw",
                "outdoor_temperature_c", "hvac_electricity_kwh",
                "cooling_electricity_kwh", "heating_electricity_kwh",
                "fan_electricity_kwh",
            ) if column in frame
        ]
        bounded, info = bounded_frame(
            frame[wanted], start=start, end=end, aggregation=aggregation,
            limit=effective_limit, maximum=context.settings.max_telemetry_records,
        )
        return {"records": bounded, "facility_values_duplicated_by_zone": False, **info}
    return execute_tool(context, "get_facility_telemetry", inputs, handler)


__all__ = ["get_facility_summary", "get_facility_telemetry"]
