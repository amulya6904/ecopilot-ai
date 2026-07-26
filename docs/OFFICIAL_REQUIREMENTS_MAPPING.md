# Official Requirements Mapping

Statuses are deliberately conservative. “Development-only” means the lightweight
harness exercises the concept but cannot satisfy official EnergyPlus evidence.

| Official requirement | Current status | Existing support | Remaining work | Planned phase |
|---|---|---|---|---|
| EnergyPlus simulation | Implemented through Phase 9 | Verified 26.1 batch and Runtime API runners | Matched comparison remains Phase 10 | 4–9 |
| IDF building model | Implemented for Phase 5 | Preserved base, Phase 4 telemetry IDF, derived fixed baseline IDF | Future agent input must reuse frozen identity | 4–5 |
| EPW weather file | Implemented | Configured Bengaluru EPW and readiness validation | Preserve matched weather in later comparisons | 4 |
| EnergyPlus Python wrapper | Implemented | Explicit batch backend plus Runtime API callbacks | None for Phase 9 | 4, 8–9 |
| Telemetry streaming | Implemented for controlled zone | Live Runtime API temperature, setpoints, occupancy, humidity and demand | Broader building scope is future | 8–9 |
| Zone temperatures | Implemented | Hourly Zone Mean Air Temperature | Fixed baseline comparison remains Phase 5 | 4 |
| Energy consumption | Implemented | Hourly Electricity:Facility, J-to-kWh | Savings comparison remains Phase 10 | 4 |
| Occupancy | Implemented for baseline | Real hourly Zone People Occupant Count; frozen People schedule inventory | Reuse unchanged in agent run | 5 |
| Indoor air quality | Development-only | Lightweight CO2 | Configure supported EnergyPlus IAQ outputs | 4 |
| PMV | Explicitly unavailable | Output requested; retained People objects do not enable Fanger PMV/PPD; nulls preserved | Future model change would require a new frozen baseline | 5 |
| Peak demand | Implemented | Direct hourly facility demand, W-to-kW, official baseline KPI | Compare only after matched agent run | 4–5 |
| Open-source LLM | Implemented for advisory analysis | Local Ollama, configurable model, structured output | Execution remains out of scope | 7 |
| MCP server | Implemented | Official SDK stdio server, 16 tools and six resources | Remote transport is not required | 6 |
| Tool calling | Implemented for advisory analysis | 12 read-only allowlisted tools and bounded loop | Execution tools remain excluded | 6–7 |
| Runtime error extraction | Implemented | Warning/severe/fatal parser and metadata | Future LLM summaries remain out of scope | 4 |
| Simulation log parsing | Implemented | Raw error preservation and warning classification | None for Phase 4 | 4 |
| Structured control actions | Implemented through safety authority | Strict Phase 7 proposal, Phase 8 candidate, Phase 9 decision | Matched optimization remains Phase 10 | 7–9 |
| Forward injection | Implemented | One verified `SPACE1-1` cooling-setpoint actuator and reset | No expansion in Phase 9 | 8–9 |
| Closed-loop operation | Implemented for validation | Manual, mock, LLM-assisted and safety-clamped runtime paths | Final comparison remains Phase 10 | 8–9 |
| Official EnergyPlus baseline | Implemented | Frozen hashes, fixed thermostat policy, official artifacts and repeatability proof | Reuse exact inputs for future agent run | 5 |
| Facility energy benchmark | Implemented | Hourly facility electricity converted once from joules | Future matched comparison | 5 |
| Comfort benchmark | Implemented | Occupied conditioned-zone temperature compliance; plenum excluded | PMV unavailable in retained model | 5 |
| Baseline comparison | Partially implemented | Official reference case exists; no agent case or savings result | Run matched agent scenario | 10 |
| kWh savings percentage | Not implemented | No savings claims | Calculate from matched official runs | 10 |
| Comfort safety intervention | Implemented for Phase 9 validation | Occupancy-aware genuine PMV path or explicit temperature proxy | Final matched proof remains Phase 10 | 9–10 |
| GitHub source code | Partially implemented | Local source repository | Publish final reviewed source | 12 |
| Architecture document | Implemented | `docs/SYSTEM_ARCHITECTURE.md` | Maintain as implementation evolves | 4–12 |
| Presentation | Not implemented | Assets directory boundary | Create final deck | 12 |
| Three-minute video | Not implemented | None | Record and edit demonstration | 12 |

Neither a placeholder nor a directory scaffold is evidence that the corresponding
runtime capability works.

Phase 5 establishes the official fixed-schedule EnergyPlus baseline using the
existing verified EnergyPlus example model. Original EnergyPlus zone identifiers
are preserved, while display aliases are used for presentation. This phase does
not implement MCP, an open-source LLM, actuator injection, autonomous control,
optimization, or savings comparison.

## Phase 6 requirements

| Requirement | Status |
|---|---|
| MCP server | Implemented |
| Tool discovery | Implemented |
| EnergyPlus data tools | Implemented |
| Official baseline execution tool | Implemented |
| Runtime-error tool | Implemented |
| Audit logging | Implemented |
| Open-source LLM | Not implemented |
| Actuator injection | Not implemented |
| Closed loop | Not implemented |

Phase 6 uses the official MCP Python SDK `mcp==1.28.1`, local stdio, bounded
structured responses, configured artifact roots, and controlled reuse of the
existing Phase 5 runner.

## Phase 7 requirements

| Requirement | Status |
|---|---|
| Ollama and configured-model discovery | Implemented |
| Read-only MCP tool calling | Implemented |
| One-zone structured advisory proposal | Implemented |
| Independent deterministic validation | Implemented |
| Bounded retries, context, audit and artifacts | Implemented |
| Application, actuators, closed loop, optimization, savings | Not implemented |

Phase 7 connects a local open-source LLM to the verified Phase 6 MCP tool layer.
The Phase 7 component remains advisory. Phases 8–9 separately implement candidate
conversion, deterministic safety authority, runtime execution, observation, and
recovery. Optimization results and savings comparison remain unimplemented.

## Phase 8–9 requirements

| Requirement | Status |
|---|---|
| EnergyPlus Python Runtime API callbacks | Implemented and runtime-validated |
| Cooling-setpoint actuator for `SPACE1-1` | Implemented and observed |
| Baseline reset and fallback | Implemented and observed |
| Deterministic final safety authority | Implemented |
| Unified strict safety state | Implemented |
| Genuine PMV/PPD path | Implemented when data exists; unavailable in retained model |
| Explicit occupied-temperature proxy | Implemented and used for retained model |
| Demand warning/critical guardrails | Implemented with prototype thresholds |
| Bounds, delta, deadband, hold, rate, oscillation | Implemented |
| Post-action verification and linked observation | Implemented |
| Rollback and emergency autonomy disablement | Implemented and fault-tested |
| 22-scenario deterministic fault suite | Implemented |
| Final optimization and savings comparison | Not implemented; Phase 10 |

Phase 9 adds deterministic safety, comfort, PMV, demand, freshness, rate, and
actuator-health supervision to the verified Phase 8 runtime-control path. PMV is
used only when genuinely available; otherwise the system explicitly uses an
occupied-temperature proxy. This phase validates safety intervention and recovery,
not final optimization or savings.
