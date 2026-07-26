# Agent Prompting and Structured Output

Prompt version `phase7-advisory-v1` defines a fixed system policy and a task plus
JSON Schema user message. Official MCP data is the source of truth. The policy
prohibits fabricated telemetry and PMV substitution, permits one occupied
non-plenum cooling advisory, and requires the proposal to remain unapplied.

Tool payloads are untrusted data. They stay in tool-role messages and are never
concatenated into the system prompt. Suspicious command-like instructions are
replaced before reaching the model.

The final response is parsed into strict Pydantic models with unknown fields
forbidden. Literal flags require advisory and safety review to be true and
applied, closed-loop, optimized-result, and savings-result to be false.

Malformed JSON, schema mismatch, unknown or plenum zones, invalid bounds or
delta, unsupported PMV claims, missing evidence, current-setpoint mismatch, or an
applied-action claim produces a concise correction prompt. It includes the
original task, validation errors, a schema reminder, and a prohibition on adding
unsupported facts. Retries and tool rounds are independently bounded.
