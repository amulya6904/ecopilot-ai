"""Read-only project, EnergyPlus, and output readiness tools."""

from dataclasses import asdict
from importlib.metadata import version
from typing import Any

from mcp_service.context import MCPApplicationContext
from mcp_service.tools import execute_tool


def get_energyplus_readiness(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        availability = context.backend_factory().availability_status()
        data = asdict(availability)
        for key in ("executable_path", "installation_dir", "idd_path"):
            if data.get(key):
                data[key] = "[configured locally]"
        return data
    return execute_tool(
        context, "get_energyplus_readiness", {}, handler,
        classification="energyplus_readiness",
    )


def get_phase_status(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        summary_available = context.artifact_path("summary.json").is_file()
        return {
            "phases": [
                {"phase": number, "status": "complete"}
                for number in range(1, 7)
            ] + [
                {"phase": number, "status": "not_implemented"}
                for number in range(7, 13)
            ],
            "phase_5_official_artifacts_available": summary_available,
            "phase_6_scope": "local MCP tools and read-only resources",
        }
    return execute_tool(context, "get_phase_status", {}, handler, classification="project_status")


def get_available_outputs(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        summary = context.load_json("summary.json")
        available = summary.get("actual_available_outputs", {})
        source_columns = {
            "zone_temperature": "indoor_temperature_c",
            "outdoor_temperature": "outdoor_temperature_c",
            "cooling_setpoint": "cooling_setpoint_c",
            "heating_setpoint": "heating_setpoint_c",
            "occupancy": "occupancy",
            "humidity": "relative_humidity_percent",
            "electricity": "interval_electricity_kwh",
            "demand": "facility_demand_kw",
            "pmv": "pmv",
            "ppd": "ppd_percent",
            "co2": None,
        }
        mapping = {
            "zone_temperature": "zone_temperature",
            "outdoor_temperature": "outdoor_temperature",
            "cooling_setpoint": "cooling_setpoint",
            "heating_setpoint": "heating_setpoint",
            "occupancy": "occupancy",
            "humidity": "zone_relative_humidity",
            "electricity": "facility_electricity",
            "demand": "facility_demand",
            "pmv": "pmv",
            "ppd": "ppd",
            "co2": "co2",
        }
        return {
            name: {
                "available": bool(available.get(mapping[name], False)),
                "source_column": source_columns[name],
            }
            for name in source_columns
        }
    return execute_tool(context, "get_available_outputs", {}, handler)


def get_system_status(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        availability = context.backend_factory().availability_status()
        baseline = context.artifact_path("summary.json").is_file()
        try:
            installed_sdk = version("mcp")
        except Exception:
            installed_sdk = None
        return {
            "project": "EcoPilot AI",
            "current_phase": 6,
            "energyplus_status": "ready" if availability.ready_for_run else "unavailable",
            "baseline_status": "available" if baseline else "not_available",
            "mcp_status": "ready",
            "active_backend": "energyplus",
            "server_name": context.settings.server_name,
            "server_version": context.settings.server_version,
            "mcp_sdk_version": installed_sdk,
            "transport": context.settings.protocol_transport,
            "read_only_default": context.settings.read_only_default,
            "baseline_run_tool_enabled": context.settings.baseline_run_tool_enabled,
            "control_tools_enabled": False,
            "audit_log_status": (
                "degraded" if context.audit_logger.last_error else "available"
            ),
            "audit_diagnostic": context.audit_logger.last_error,
        }
    return execute_tool(context, "get_system_status", {}, handler, classification="project_status")


__all__ = [
    "get_available_outputs", "get_energyplus_readiness", "get_phase_status",
    "get_system_status",
]
