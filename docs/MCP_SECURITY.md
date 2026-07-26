# Phase 6 MCP security

The MCP caller cannot supply executable, IDF, EPW, output, audit, or log paths;
shell commands; Python expressions; or environment variables. Pydantic request
models forbid extra fields. Artifact reads resolve under the configured official
results root, and manifest machine paths are redacted.

The MCP service does not use `eval`, `exec`, `shell=True`, unrestricted file
access, or caller-selected subprocesses. There are no control, actuator, schedule
editing, setpoint modification, optimization, LLM, or closed-loop tools.

Responses are recursively converted to strict JSON, reject binary/unknown values,
map NaN/NaT to null, enforce depth and byte limits, and return bounded DataFrame
records. PMV/PPD remain null with a reason when EnergyPlus did not produce them.

Every tool call appends one JSON Lines audit record to
`results/audit/mcp_tool_calls.jsonl`. Records include the audit ID, timestamp,
tool, sanitized inputs, success, duration, record count, result size, error code,
source, and classification. They never include telemetry payloads, raw files,
secrets, tracebacks, or environment values. Audit writes are thread-safe; an audit
write failure leaves the tool result intact and appears in system diagnostics.

Public error codes are:

`INVALID_REQUEST`, `INVALID_ZONE`, `INVALID_DATE_RANGE`,
`INVALID_AGGREGATION`, `LIMIT_EXCEEDED`, `ARTIFACT_NOT_FOUND`,
`ENERGYPLUS_UNAVAILABLE`, `BASELINE_NOT_AVAILABLE`,
`RUN_ALREADY_IN_PROGRESS`, `TOOL_TIMEOUT`, `TOOL_EXECUTION_FAILED`,
`RESPONSE_TOO_LARGE`, and `INTERNAL_ERROR`.

The controlled runner uses a non-blocking single-process lock and releases it on
success, failure, and timeout. This is adequate for the Phase 6 local stdio server,
not for multi-process deployment.
