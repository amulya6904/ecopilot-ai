# System Architecture

## 1. Problem overview

EcoPilot AI must reduce HVAC energy while respecting comfort, indoor-air-quality,
equipment, peak-demand, and carbon constraints. Official evidence must come from
matched EnergyPlus simulations, not the lightweight development model.

## 2. Official target architecture

```text
EnergyPlus IDF + EPW
        ↓
EnergyPlus runtime/API
        ↓
Telemetry and log adapter
        ↓
Building backend abstraction
        ↓
MCP tool server
        ↓
Open-source LLM agent
        ↓
Structured control proposal
        ↓
Deterministic safety validator
        ↓
Setpoint/actuator injection
        ↓
EnergyPlus next interval
        ↓
Dashboard, logs and audit history
```

This design is implemented through the deterministic Phase 9 safety and recovery
boundary. Phase 10 optimization and matched savings comparison are not implemented.

## 3. Current development architecture

The implemented path is configuration → `BuildingSimulator` → fixed schedule
controller → development metrics → CLI/Streamlit. It uses seeded three-zone
equations and produces 432 records. `LightweightSimulatorBackend` now exposes that
path through the shared contract.

## 4. Backend abstraction

`BuildingBackend` defines identity, availability, reset, time, completion, step,
history, and runtime-error operations. Explicit backend creation prevents an
EnergyPlus request from silently becoming a lightweight run.

## 5. Lightweight simulator role

The lightweight backend is a development harness and fallback for interface, data,
controller, metric, and UI tests. Composition preserves the existing equations,
random seed, heat-wave behavior, default actions, and history.

## 6. Phase 4 EnergyPlus backend

The backend validates executable, IDD, IDF, EPW, version, and output readiness;
runs EnergyPlus as an isolated subprocess; preserves raw outputs and metadata;
classifies diagnostics; and parses zone and building telemetry. It never silently
substitutes the lightweight backend.

Zone telemetry contains one row per zone and timestamp. Building telemetry contains
one row per timestamp for `Electricity:Facility [J](Hourly)` and
`Whole Building:Facility Total Electricity Demand Rate [W](Hourly)`. This separation
prevents facility totals from being multiplied by zone count. Electricity uses
J / 3,600,000 and direct demand uses W / 1,000.

The accepted `weather_location_mismatch` warning records that the example IDF
Location is Chicago while the EPW is Bengaluru; EnergyPlus uses the EPW location.
The complete diagnostic is retained in metadata.

## 7. Phase 5 official baseline pipeline

```text
Verified Phase 4 IDF + frozen EPW
        ↓
Object-level schedule inspection
        ↓
Derived fixed-thermostat IDF
        ↓
Phase 4 subprocess runner
        ↓
Normalized zone + facility telemetry
        ↓
Energy, demand, temperature, PMV-availability and adherence metrics
        ↓
Official artifacts + frozen manifest + reproducibility comparison
```

Option A preserves the verified example geometry and exact EnergyPlus zone names.
The central mapping supplies display aliases for the UI. `PLENUM-1` remains in raw
telemetry and is excluded from occupied comfort and thermostat adherence. The five
`SPACE*-1` zones use shared Phase 5 cooling and heating schedules. Existing
occupancy and internal-load schedules are preserved.

The normalizer separates one facility record per timestamp from one record per
timestamp and EnergyPlus zone. Yearless hourly EnergyPlus timestamps are interpreted
as interval ends with reference year 2000; `24:00` rolls to the next calendar day.
Unavailable PMV/PPD stays null and is documented.

The manifest freezes EnergyPlus version, executable, source/derived/weather hashes,
run period, schedules, zone mapping, requested and actual outputs, and diagnostics.
The reproducibility checker compares exact inputs, telemetry shapes, warnings,
energy, peak demand, thermostat adherence, temperature compliance, and PMV
compliance when available.

## 8. Telemetry schema

`BuildingState` carries timestamps, source, zone identity, indoor/outdoor
temperature, occupancy, humidity, optional CO2, optional PMV, comfort status,
setpoints, fan/ventilation controls, power, interval/cumulative energy, optional
facility peak demand, price, and carbon intensity. Unavailable telemetry is `None`,
not zero.

## 9. Runtime-error schema

`RuntimeErrorRecord` contains timestamp, source, severity, code, message, a bounded
raw excerpt, and recoverability. It is suitable for later MCP error tools without
putting an entire log in a model prompt.

## 10. Control-action schema

`ControlAction` identifies the zone, cooling/heating setpoints, optional fan and
ventilation values, action source, reason, confidence, request time, and validation
result. Current actions are `baseline_schedule` or `fixed_test_action`, never AI.

## 11. MCP tool architecture

Phase 6 bounded tools read summarized state, constraints, demand, carbon, recent
actions, and relevant errors. Tools enforce input schemas and least authority.
They cannot write schedules, actuators, thermostats, or setpoints.

## 12. LLM prompting approach

The Phase 7 open-source model receives a compact system policy, current targets and
constraints, summarized official evidence, relevant errors, and bounded tool
schemas. Prompts distinguish observations from unavailable fields and require
explicit reasons.

## 13. Structured response format

The agent response will be machine-validated JSON matching control proposal
schemas, including per-zone values, reason, confidence, horizon, and constraint
acknowledgements. Natural-language prose will not be accepted as an actuator input.

## 14. Safety-validation layer

Deterministic checks will enforce absolute equipment bounds, rate limits, PMV or
temperature fallback constraints, CO2/ventilation constraints, demand policy,
conflict handling, stale-state rejection, and operator overrides. Rejected actions
fall back to a known schedule and are audited.

## 15. Forward injection

Phase 8 maps a validated cooling-setpoint candidate to the selected Runtime API
actuator and applies it before the next interval. Phase 9 now provides final
deterministic authority and post-action verification. Phase 5 remains the
deterministic fallback schedule.

## 16. Latency-management strategy

Agent calls will have a timeout, bounded retries, and a deterministic fallback
schedule. Telemetry will be summarized to the useful horizon rather than sending
every record. Full raw logs will not be included in every prompt. A late response
will be rejected for its expired interval.

## 17. Long-log management

The runtime layer will extract errors, summarize repeated warnings, retain raw logs
on disk, send only relevant excerpts to the LLM, and preserve references to the
full log files for operators and audits.

## 18. Baseline-versus-agent comparison

Official runs must use identical EnergyPlus IDF, EPW, timestep, warm-up, seeds where
applicable, output variables, and evaluation windows. Reports will compare total
kWh, percentage reduction, peak demand, cost/carbon, PMV compliance, IAQ, and
violations. Development outputs remain separate.

## 19. Failure recovery

The coordinator will detect runtime failure, timeout, invalid telemetry, malformed
agent output, validation rejection, and actuator failure. It will record the error,
apply a deterministic safe schedule when possible, stop on unrecoverable
EnergyPlus errors, and surface status without fabricating telemetry.

## 20. IDF versioning

The source baseline will live under `energyplus/models/`. Generated or modified
runtime IDFs will live under `energyplus/models/modified/` with run IDs, timestamps,
input hashes, and provenance. Source IDFs are not globally ignored.

## 21. Audit logging

Each interval will link source telemetry, summarized prompt context, tool calls,
model response, proposed action, validation outcome, applied override, runtime
errors, and resulting telemetry. Logs must make fallback and human intervention
visible. Phase 7, Phase 8, and Phase 9 write separate bounded audit streams and
linked artifact bundles.

Phase 5 establishes the official fixed-schedule EnergyPlus baseline using the
existing verified EnergyPlus example model. Original EnergyPlus zone identifiers
are preserved, while display aliases are used for presentation. This phase does not
implement MCP, an open-source LLM, actuator injection, autonomous control,
optimization, or savings comparison.

## Phase 6 MCP boundary

```text
MCP client
    | local stdio (official mcp==1.28.1 SDK)
FastMCP server
    | strict validation, response limits, audit, error translation
MCPApplicationContext
    +-- EnergyPlus discovery/backend
    +-- existing Phase 5 official baseline runner
    +-- frozen JSON/CSV artifacts and manifest
    +-- normalized telemetry, metrics, and diagnostics
```

The MCP layer loads persisted normalized products rather than duplicating raw
EnergyPlus parsing or baseline metric calculation. Its only execution tool invokes
`run_energyplus_baseline()` with configured paths under a single-process lock.
No MCP tool modifies a schedule, actuator, thermostat, or setpoint.

Phase 6 exposes the verified EnergyPlus and official baseline capabilities through a local MCP server. The server provides bounded, validated tools and read-only resources. It does not yet include an open-source LLM, autonomous reasoning, actuator injection, optimization, or closed-loop control.

## Phase 7 advisory-agent boundary

```text
local Ollama
    -> bounded structured chat
Phase 7 AdvisoryAgent
    -> 12 read-only tools over official MCP stdio
Phase 6 official EnergyPlus baseline data
    -> strict schema and deterministic validator
advisory artifacts and compact JSONL audit
```

Phase 7 connects a local open-source LLM to the verified Phase 6 MCP tool layer.
The Phase 7 component remains advisory. Phases 8–9 separately implement candidate
conversion, deterministic safety authority, runtime control, observation, and
recovery. Optimization results and savings comparison remain unimplemented.

## Phase 8–9 verified runtime and safety path

```text
Phase 7 structured advisory (optional)
        |
        v
Phase 8 executable candidate + preliminary runtime validation
        |
        v
Phase 9 strict SafetyStateSnapshot
        |
        v
Deterministic rule evaluation and SafetyDecision
        |
        +-- approve / approve_with_clamp --> Phase 8 single actuator write
        |
        +-- hold / reject / fallback / emergency_fallback
                                             |
                                             v
                                  Phase 8 baseline reset
        |
        v
Phase 9 post-action verification --> rollback/emergency evidence
```

The callback before HVAC managers owns the one actuator application site. The
end-zone-timestep callback observes the resulting cooling setpoint, populates the
linked Phase 8 `observed_setpoint_after_application` field, and invokes the Phase 9
post-action verifier. Phase 9 never creates a second actuator mechanism.

Phase 9 adds deterministic safety, comfort, PMV, demand, freshness, rate, and
actuator-health supervision to the verified Phase 8 runtime-control path. PMV is
used only when genuinely available; otherwise the system explicitly uses an
occupied-temperature proxy. This phase validates safety intervention and recovery,
not final optimization or savings.
