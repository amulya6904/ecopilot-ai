# Phase 6 MCP tools

Phase 6 exposes the verified EnergyPlus and official baseline capabilities through a local MCP server. The server provides bounded, validated tools and read-only resources. It does not yet include an open-source LLM, autonomous reasoning, actuator injection, optimization, or closed-loop control.

The implementation uses the official Model Context Protocol Python SDK `mcp==1.28.1`
and its stable v1 FastMCP API. The primary and only Phase 6 transport is local
stdio. Importing `mcp_service.server` creates no process; `create_mcp_server()`
registers the service and `run_stdio_server()` starts it.

## Tool catalogue

| Category | Tools |
|---|---|
| System | `get_system_status`, `get_energyplus_readiness`, `get_phase_status`, `get_available_outputs` |
| Baseline | `get_official_baseline_summary`, `get_baseline_manifest`, `get_latest_energyplus_run`, `run_official_baseline` |
| Zones | `list_zones`, `get_zone_summary`, `get_zone_telemetry` |
| Facility | `get_facility_summary`, `get_facility_telemetry` |
| Comfort | `get_comfort_summary`, `get_thermostat_adherence` |
| Diagnostics | `get_runtime_errors` |

All calls return `success`, `tool_name`, `data`, `error`, and `metadata`.
Metadata contains timestamps, duration, source, backend, classification, record
count, truncation state, and an audit ID. Errors use stable codes documented in
`MCP_SECURITY.md`; Python tracebacks are never returned.

`run_official_baseline` is the sole execution tool. It accepts only
`verify_reproducibility` and `force_rebuild`, invokes the existing Phase 5 runner,
uses configured paths, holds a single-process execution lock, never uses the
lightweight backend, and never changes a live control.

Telemetry accepts an optional inclusive ISO-8601 date range, `raw`, `hourly`, or
`daily` aggregation, and a record limit. Defaults are 200 records and the maximum
is 500. Error queries are capped at 100 records, raw diagnostic messages at 10,000
characters, and every response at 1,000,000 JSON bytes.

## Resources

All resources are bounded, JSON, and read-only:

- `ecopilot://project/status`
- `ecopilot://energyplus/readiness`
- `ecopilot://baseline/summary`
- `ecopilot://baseline/manifest`
- `ecopilot://zones`
- `ecopilot://errors/latest`

## Local lifecycle and client configuration

Install dependencies and start the server:

```powershell
python -m pip install -r requirements.txt
python -m scripts.run_phase6_mcp_server
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "ecopilot-energyplus": {
      "command": "python",
      "args": ["-m", "scripts.run_phase6_mcp_server"],
      "cwd": "C:/path/to/ecopilot-ai"
    }
  }
}
```

The real SDK smoke client does not run EnergyPlus by default:

```powershell
python -m scripts.test_phase6_mcp_client
python -m scripts.test_phase6_mcp_client --run-baseline
```

The execution lock protects one local server process. A future multi-process or
remote deployment needs an inter-process/distributed lock. Phase 7 may consume
these tools from an open-source LLM, but no LLM integration is part of Phase 6.

On Windows, the bundled smoke client disables the official SDK transport's
optional descendant-cleanup Job Object because nested Job Objects severely
throttle EnergyPlus in some managed shells. It still uses the official
`stdio_client` and `ClientSession` protocol APIs, and normal stdio shutdown still
terminates the server. The server's execution lock and timeout remain active.

## Phase 7 model allowlist

The model receives `get_system_status`, `get_energyplus_readiness`,
`get_official_baseline_summary`, `get_available_outputs`, `list_zones`,
`get_zone_summary`, `get_zone_telemetry`, `get_facility_summary`,
`get_facility_telemetry`, `get_comfort_summary`,
`get_thermostat_adherence`, and `get_runtime_errors`.

`run_official_baseline`, paths, commands, actuator access, and control application
are excluded. Phase 7 validates each selected name and its JSON arguments.
