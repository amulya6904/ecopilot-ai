"""Bounded, read-only MCP resource documents."""

import json
from typing import Any, Callable

from mcp_service.context import MCPApplicationContext
from mcp_service.tools.baseline_tools import (
    get_baseline_manifest,
    get_official_baseline_summary,
)
from mcp_service.tools.diagnostic_tools import get_runtime_errors
from mcp_service.tools.system_tools import (
    get_energyplus_readiness,
    get_system_status,
)
from mcp_service.tools.zone_tools import list_zones


RESOURCE_CATALOGUE: tuple[dict[str, str], ...] = (
    {"uri": "ecopilot://project/status", "title": "EcoPilot project status"},
    {"uri": "ecopilot://energyplus/readiness", "title": "EnergyPlus readiness"},
    {"uri": "ecopilot://baseline/summary", "title": "Official baseline summary"},
    {"uri": "ecopilot://baseline/manifest", "title": "Frozen baseline manifest"},
    {"uri": "ecopilot://zones", "title": "EnergyPlus zones and aliases"},
    {"uri": "ecopilot://errors/latest", "title": "Latest EnergyPlus diagnostics"},
)


def resource_loaders(context: MCPApplicationContext) -> dict[str, Callable[[], Any]]:
    return {
        "ecopilot://project/status": lambda: get_system_status(context),
        "ecopilot://energyplus/readiness": lambda: get_energyplus_readiness(context),
        "ecopilot://baseline/summary": lambda: get_official_baseline_summary(context),
        "ecopilot://baseline/manifest": lambda: get_baseline_manifest(context),
        "ecopilot://zones": lambda: list_zones(context),
        "ecopilot://errors/latest": lambda: get_runtime_errors(context, limit=20),
    }


def as_json_resource(loader: Callable[[], Any]) -> str:
    return json.dumps(loader(), sort_keys=True, allow_nan=False)


__all__ = ["RESOURCE_CATALOGUE", "as_json_resource", "resource_loaders"]
