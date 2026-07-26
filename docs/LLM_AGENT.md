# Phase 7 Local LLM Agent

Phase 7 connects a local open-source LLM to the verified Phase 6 MCP tool layer.
The agent retrieves official EnergyPlus evidence and produces a validated advisory
proposal. The Phase 7 component cannot write actuators. Phases 8–9 separately own
candidate conversion, deterministic safety authority, and runtime execution.
Optimization results and savings comparison remain unimplemented.

## Setup

Install and start Ollama, then inspect readiness:

```powershell
python -m scripts.check_ollama
```

The configured default is `qwen3:4b`. Model files consume local disk, memory, and
download bandwidth, so the project never downloads one automatically. After
reviewing those costs, install it with `ollama pull qwen3:4b`, or select an
already-installed model:

```powershell
$env:ECOPILOT_LLM_MODEL = "llama3.2:latest"
python -m scripts.run_phase7_agent
```

`OLLAMA_HOST` must resolve to localhost. Timeout, temperature, tool rounds, and
retry count are controlled by the environment variables in `llm/settings.py`.

## Workflow

The agent starts Phase 6 over local stdio, initializes the official MCP client,
discovers tools, filters them through a 12-tool read-only allowlist, and converts
their schemas to Ollama tool definitions. It validates selected names and
arguments, calls MCP, bounds tool results, and returns them only as tool messages.

The final response must match the strict `ControlProposal` schema. An independent
validator checks zone and alias, occupied/non-plenum role, comfort inclusion,
current setpoint evidence, cooling limits, maximum change, heating deadband,
evidence provenance, occupancy source, and PMV availability. Invalid proposals
receive at most two correction attempts.

Tool results are capped at 20,000 characters and context at 50,000 characters.
Ollama calls have a configurable 300-second default timeout for CPU-only model
loading and prompt evaluation. Compact audit
metadata goes to `results/audit/agent_runs.jsonl`; detailed advisory artifacts go
under `results/agent/phase7/<run-id>/`.

The proposal is qualitative. It does not establish causality, quantify reduction,
prove comfort preservation, or apply control. Phase 8 requires separately
authorized safety and runtime integration.

## Phase 9 execution boundary

The Phase 7 model remains advisory. A structured proposal is normalized into a
Phase 8 executable candidate and then evaluated by the Phase 9 deterministic
safety supervisor. Model confidence cannot override any failed rule, and raw model
content cannot call `set_actuator_value`. A timeout or invalid proposal selects a
deterministic fallback candidate that is still subject to Phase 9.

Phase 9 adds deterministic safety, comfort, PMV, demand, freshness, rate, and
actuator-health supervision to the verified Phase 8 runtime-control path. PMV is
used only when genuinely available; otherwise the system explicitly uses an
occupied-temperature proxy. This phase validates safety intervention and recovery,
not final optimization or savings.
