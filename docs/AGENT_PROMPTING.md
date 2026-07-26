# Agent prompting contract

## Design goal

Prompting supports a small, auditable advisory decision. It does not grant
control authority, ask for private reasoning, or ask the model to recreate a
large schema in prose.

## System prompt responsibilities

The stable system prompt:

- defines the model as an advisory building-energy analyst;
- restricts evidence to bounded official MCP results;
- forbids direct control, optimization, and savings claims;
- requires the exact supported EnergyPlus zone;
- distinguishes an advisory proposal from an applied action;
- requests only the compact structured fields;
- directs uncertainty into confidence and reason, not invented telemetry.

## Evidence prompt responsibilities

The user message contains compact, sanitized facts selected by Python:

- EnergyPlus readiness and official classification;
- baseline facility and controlled-zone evidence;
- current setpoint and configured bounds;
- comfort-proxy and PMV availability;
- demand state when available;
- explicit advisory objective.

Raw annual telemetry and the complete MCP conversation are excluded.

## Final schema

`LLMDecision.model_json_schema()` is supplied through Ollama's `format` field.
The final request contains two messages, no tools, `stream=False`, and
`think=False`. Output is limited to:

- `energyplus_zone_name`;
- `proposed_setpoint_c`;
- `objective`;
- `confidence`;
- `reason`.

Python adds all deterministic metadata and validates the response. Prompt text
is versioned, and prompt length, schema length, token cap, timings, and evidence
mode are recorded without storing hidden chain-of-thought.

## Failure discipline

Unsupported evidence, malformed JSON, invalid values, timeout, MCP failure, and
missing model readiness have distinct typed errors. The live UI permits one
proposal retry. No failed proposal reaches an actuator, and any fallback is
clearly classified.

For latency limits, callback separation, and Phase 10 policy rationale, see
[Local LLM, prompt, and latency design](LLM_AGENT.md).
