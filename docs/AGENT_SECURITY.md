# Phase 7 Agent Security

The Phase 7 trust boundary treats model output and MCP content as untrusted. Only
12 named read-only tools are exposed. Each function name is allowlisted and every
argument object is checked against the MCP JSON Schema.

The model cannot select paths, commands, scripts, environment values, Python or
shell execution, baseline reruns, actuator handles, schedule modification, or
action application. The implementation uses no `eval`, `exec`, or `shell=True`.

Response and context limits prevent unbounded telemetry from entering the
prompt. Raw log excerpts are excluded, command-like content is sanitized,
network access is restricted to localhost Ollama, and imports do not contact
Ollama or start MCP.

Strict proposal literals prevent execution/result flags from changing. The
validator checks assertions against the MCP history and rejects citations to
tools that were not called. Compact JSONL audit records omit tool payloads;
detailed artifacts remain under a configured repository path.

Phase 7 cannot mutate EnergyPlus. It adds no fallback control, actuator injection,
closed-loop execution, optimization, or savings comparison.

## Phase 9 final authority

No agent response is an actuator command. Only strict `ExecutableActionCandidate`
objects enter the supervisor, and only `approve` or `approve_with_clamp` may reach
the one Phase 8 write location. Run ID, zone, telemetry, bounds, direction,
comfort, demand, rate, oscillation, and actuator health are independently checked.
Safety settings forbid autonomous bypass. Audit records contain state summaries,
rules, and decisions, never hidden model reasoning.
