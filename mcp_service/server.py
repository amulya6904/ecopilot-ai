"""Official MCP SDK server creation and isolated stdio execution."""

import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_service.context import MCPApplicationContext, create_application_context
from mcp_service.resources import RESOURCE_CATALOGUE, as_json_resource, resource_loaders
from mcp_service.settings import MCPSettings
from mcp_service.tools.baseline_tools import (
    get_baseline_manifest,
    get_latest_energyplus_run,
    get_official_baseline_summary,
    run_official_baseline,
)
from mcp_service.tools.comfort_tools import (
    get_comfort_summary,
    get_thermostat_adherence,
)
from mcp_service.tools.diagnostic_tools import get_runtime_errors
from mcp_service.tools.facility_tools import (
    get_facility_summary,
    get_facility_telemetry,
)
from mcp_service.tools.system_tools import (
    get_available_outputs,
    get_energyplus_readiness,
    get_phase_status,
    get_system_status,
)
from mcp_service.tools.zone_tools import (
    get_zone_summary,
    get_zone_telemetry,
    list_zones,
)


READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
EXECUTION = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)


def create_mcp_server(
    context: MCPApplicationContext | None = None,
    settings: MCPSettings | None = None,
) -> FastMCP:
    """Create and register the Phase 6 server without starting any transport."""
    application = context or create_application_context(settings)
    if settings is not None and context is not None and context.settings != settings:
        raise ValueError("Injected context and settings must agree.")
    server = FastMCP(
        application.settings.server_name,
        instructions=(
            "Provides bounded, validated EnergyPlus-derived official baseline data. "
            "Phase 6 has no control, setpoint, actuator, optimization, or LLM tools."
        ),
        log_level="ERROR",
    )
    server.ecopilot_context = application  # type: ignore[attr-defined]

    @server.tool(name="get_system_status", description="Return project, EnergyPlus, official-baseline, MCP, SDK, and audit readiness. Read-only; no control modification.", annotations=READ_ONLY, structured_output=True)
    def get_system_status_tool() -> dict[str, Any]:
        return get_system_status(application)

    @server.tool(name="get_energyplus_readiness", description="Return Phase 4 EnergyPlus discovery and configured-input readiness. Read-only and does not run EnergyPlus.", annotations=READ_ONLY, structured_output=True)
    def readiness() -> dict[str, Any]:
        return get_energyplus_readiness(application)

    @server.tool(name="get_phase_status", description="Return honest EcoPilot phase completion status. Read-only; later LLM and closed-loop phases remain unimplemented.", annotations=READ_ONLY, structured_output=True)
    def phase_status() -> dict[str, Any]:
        return get_phase_status(application)

    @server.tool(name="get_available_outputs", description="Return availability booleans and normalized source columns for official EnergyPlus baseline outputs. Read-only.", annotations=READ_ONLY, structured_output=True)
    def outputs() -> dict[str, Any]:
        return get_available_outputs(application)

    @server.tool(name="get_official_baseline_summary", description="Read the persisted Phase 5 EnergyPlus-derived official baseline summary without recalculating it.", annotations=READ_ONLY, structured_output=True)
    def baseline_summary() -> dict[str, Any]:
        return get_official_baseline_summary(application)

    @server.tool(name="get_baseline_manifest", description="Read the frozen Phase 5 EnergyPlus baseline hashes and configuration with machine-sensitive paths redacted.", annotations=READ_ONLY, structured_output=True)
    def baseline_manifest() -> dict[str, Any]:
        return get_baseline_manifest(application)

    @server.tool(name="get_latest_energyplus_run", description="Return compact metadata for the latest official EnergyPlus simulation or baseline. Does not trigger execution.", annotations=READ_ONLY, structured_output=True)
    def latest_run() -> dict[str, Any]:
        return get_latest_energyplus_run(application)

    @server.tool(name="run_official_baseline", description="Trigger only the existing controlled Phase 5 EnergyPlus baseline runner using configured paths. It never modifies live controls and never falls back to the lightweight simulator.", annotations=EXECUTION, structured_output=True)
    async def baseline_run(verify_reproducibility: bool = False, force_rebuild: bool = False) -> dict[str, Any]:
        return run_official_baseline(
            application,
            verify_reproducibility=verify_reproducibility,
            force_rebuild=force_rebuild,
        )

    @server.tool(name="list_zones", description="List official EnergyPlus technical zone names, display aliases, roles, comfort inclusion, and data availability. Read-only baseline data.", annotations=READ_ONLY, structured_output=True)
    def zones() -> dict[str, Any]:
        return list_zones(application)

    @server.tool(name="get_zone_summary", description="Return one persisted EnergyPlus baseline zone summary resolved by exact technical name or display alias. Plenums are marked excluded from occupied comfort.", annotations=READ_ONLY, structured_output=True)
    def zone_summary(zone_name: str) -> dict[str, Any]:
        return get_zone_summary(application, zone_name)

    @server.tool(name="get_zone_telemetry", description="Return date-filtered, aggregated, record-bounded official EnergyPlus baseline telemetry for one exact zone or alias. It does not modify controls.", annotations=READ_ONLY, structured_output=True)
    def zone_telemetry(zone_name: str, start: str | None = None, end: str | None = None, aggregation: str = "raw", limit: int = 200) -> dict[str, Any]:
        from datetime import datetime
        parsed_start = datetime.fromisoformat(start) if start else None
        parsed_end = datetime.fromisoformat(end) if end else None
        return get_zone_telemetry(
            application, zone_name, start=parsed_start, end=parsed_end,
            aggregation=aggregation, limit=limit,
        )

    @server.tool(name="get_facility_summary", description="Return persisted whole-facility EnergyPlus baseline electricity and demand metrics without zone duplication.", annotations=READ_ONLY, structured_output=True)
    def facility_summary() -> dict[str, Any]:
        return get_facility_summary(application)

    @server.tool(name="get_facility_telemetry", description="Return date-filtered, aggregated, bounded official EnergyPlus facility electricity, demand, and outdoor-temperature telemetry.", annotations=READ_ONLY, structured_output=True)
    def facility_telemetry(start: str | None = None, end: str | None = None, aggregation: str = "raw", limit: int = 200) -> dict[str, Any]:
        from datetime import datetime
        parsed_start = datetime.fromisoformat(start) if start else None
        parsed_end = datetime.fromisoformat(end) if end else None
        return get_facility_telemetry(
            application, start=parsed_start, end=parsed_end,
            aggregation=aggregation, limit=limit,
        )

    @server.tool(name="get_comfort_summary", description="Return occupied-zone temperature compliance and actual PMV/PPD availability from the official EnergyPlus baseline. Unavailable PMV values remain null.", annotations=READ_ONLY, structured_output=True)
    def comfort_summary() -> dict[str, Any]:
        return get_comfort_summary(application)

    @server.tool(name="get_thermostat_adherence", description="Return the frozen Phase 5 thermostat policy, measured EnergyPlus output adherence, mismatches, and bounded boundary samples. No setpoint modification occurs.", annotations=READ_ONLY, structured_output=True)
    def thermostat_adherence() -> dict[str, Any]:
        return get_thermostat_adherence(application)

    @server.tool(name="get_runtime_errors", description="Return filtered and bounded EnergyPlus warnings, severe errors, and fatal errors from the official baseline. Full raw logs are not returned.", annotations=READ_ONLY, structured_output=True)
    def runtime_errors(severity: str | None = None, classification: str | None = None, limit: int = 100) -> dict[str, Any]:
        return get_runtime_errors(
            application, severity=severity, classification=classification, limit=limit
        )

    loaders = resource_loaders(application)
    def bind_resource(loader):
        def read_resource() -> str:
            return as_json_resource(loader)
        return read_resource

    for resource in RESOURCE_CATALOGUE:
        uri = resource["uri"]
        loader = loaders[uri]
        server.resource(
            uri,
            name=resource["title"],
            description="Bounded read-only EcoPilot EnergyPlus resource.",
            mime_type="application/json",
        )(bind_resource(loader))
    return server


def run_stdio_server(
    context: MCPApplicationContext | None = None,
    settings: MCPSettings | None = None,
) -> None:
    """Run stdio without writing ordinary logs to protocol stdout."""
    logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
    create_mcp_server(context=context, settings=settings).run(transport="stdio")


__all__ = ["create_mcp_server", "run_stdio_server"]
