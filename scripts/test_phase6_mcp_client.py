"""Real official-SDK stdio smoke client for the EcoPilot MCP server."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


REQUIRED_TOOLS = {
    "get_system_status", "get_energyplus_readiness", "get_phase_status",
    "get_available_outputs", "get_official_baseline_summary",
    "get_baseline_manifest", "get_latest_energyplus_run",
    "run_official_baseline", "list_zones", "get_zone_summary",
    "get_zone_telemetry", "get_facility_summary", "get_facility_telemetry",
    "get_comfort_summary", "get_thermostat_adherence", "get_runtime_errors",
}
REQUIRED_RESOURCES = {
    "ecopilot://project/status", "ecopilot://energyplus/readiness",
    "ecopilot://baseline/summary", "ecopilot://baseline/manifest",
    "ecopilot://zones", "ecopilot://errors/latest",
}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EcoPilot Phase 6 MCP stdio smoke test")
    parser.add_argument("--run-baseline", action="store_true", help="also invoke the controlled official baseline run tool")
    return parser.parse_args()


def _structured(result: Any) -> dict[str, Any]:
    value = result.structuredContent
    if isinstance(value, dict):
        return value
    if result.content and hasattr(result.content[0], "text"):
        return json.loads(result.content[0].text)
    raise ValueError("Tool did not return structured JSON.")


def _apply_windows_energyplus_compatibility() -> None:
    """Avoid nested SDK Job-Object throttling of EnergyPlus on Windows.

    The official stdio transport remains in use. Only its optional process-tree
    cleanup Job Object is disabled; ClientSession still owns and terminates the
    stdio server process normally.
    """
    if sys.platform == "win32":
        import mcp.os.win32.utilities as windows_utilities
        windows_utilities._create_job_object = lambda: None


async def smoke_test(run_baseline: bool = False) -> int:
    _apply_windows_energyplus_compatibility()
    repository = Path(__file__).parents[1]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "scripts.run_phase6_mcp_server"],
        cwd=repository,
        env=dict(os.environ),
    )
    failures: list[str] = []
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            print(f"PASS initialize: {initialized.serverInfo.name}")
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            missing = REQUIRED_TOOLS - names
            print(f"{'FAIL' if missing else 'PASS'} tools/list: {len(names)} discovered")
            if missing:
                failures.append(f"missing tools: {sorted(missing)}")
            resources = await session.list_resources()
            uris = {str(resource.uri) for resource in resources.resources}
            missing_resources = REQUIRED_RESOURCES - uris
            print(f"{'FAIL' if missing_resources else 'PASS'} resources/list: {len(uris)} discovered")
            if missing_resources:
                failures.append(f"missing resources: {sorted(missing_resources)}")
            calls = [
                ("get_system_status", {}),
                ("get_energyplus_readiness", {}),
                ("get_official_baseline_summary", {}),
                ("list_zones", {}),
                ("get_zone_summary", {"zone_name": "Open Office"}),
                ("get_zone_telemetry", {"zone_name": "SPACE1-1", "limit": 3}),
                ("get_facility_summary", {}),
                ("get_facility_telemetry", {"limit": 3}),
                ("get_comfort_summary", {}),
                ("get_thermostat_adherence", {}),
                ("get_runtime_errors", {"limit": 3}),
            ]
            if run_baseline:
                calls.append(("run_official_baseline", {}))
            for name, arguments in calls:
                try:
                    response = _structured(await session.call_tool(name, arguments))
                    passed = response.get("success") is True
                    print(f"{'PASS' if passed else 'FAIL'} tools/call {name}")
                    if not passed:
                        failures.append(f"{name}: {response.get('error')}")
                except Exception as exc:
                    print(f"FAIL tools/call {name}: {type(exc).__name__}")
                    failures.append(f"{name}: {type(exc).__name__}")
    if failures:
        print("Smoke test failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Phase 6 MCP client smoke test passed.")
    return 0


def main() -> int:
    args = _arguments()
    return asyncio.run(smoke_test(run_baseline=args.run_baseline))


if __name__ == "__main__":
    raise SystemExit(main())
