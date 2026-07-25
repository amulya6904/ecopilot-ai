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

This is a target design. The EnergyPlus, MCP, LLM, safety-injection, and closed-loop
segments are not implemented.

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

## 6. Future EnergyPlus backend

The Phase 4 backend will validate executable, IDF, and EPW inputs; manage runs and
callbacks; map variables and meters; expose actuators; capture failures; and manage
output/model paths. The current placeholder is always unavailable.

## 7. Telemetry schema

`BuildingState` carries timestamps, source, zone identity, indoor/outdoor
temperature, occupancy, humidity, optional CO2, optional PMV, comfort status,
setpoints, fan/ventilation controls, power, interval/cumulative energy, optional
facility peak demand, price, and carbon intensity. Unavailable telemetry is `None`,
not zero.

## 8. Runtime-error schema

`RuntimeErrorRecord` contains timestamp, source, severity, code, message, a bounded
raw excerpt, and recoverability. It is suitable for later MCP error tools without
putting an entire log in a model prompt.

## 9. Control-action schema

`ControlAction` identifies the zone, cooling/heating setpoints, optional fan and
ventilation values, action source, reason, confidence, request time, and validation
result. Current actions are `baseline_schedule` or `fixed_test_action`, never AI.

## 10. MCP tool architecture

Future bounded tools will read summarized state, constraints, demand, carbon,
recent actions, and relevant errors; submit structured proposals; and query audit
records. Tools will enforce input schemas and least authority. No MCP server tools
exist today.

## 11. LLM prompting approach

The future open-source model will receive a compact system policy, current targets
and constraints, summarized recent telemetry, relevant errors, and available tool
schemas. Prompts will distinguish observations from unavailable fields and require
explicit reasons.

## 12. Structured response format

The agent response will be machine-validated JSON matching control proposal
schemas, including per-zone values, reason, confidence, horizon, and constraint
acknowledgements. Natural-language prose will not be accepted as an actuator input.

## 13. Safety-validation layer

Deterministic checks will enforce absolute equipment bounds, rate limits, PMV or
temperature fallback constraints, CO2/ventilation constraints, demand policy,
conflict handling, stale-state rejection, and operator overrides. Rejected actions
fall back to a known schedule and are audited.

## 14. Forward injection

After validation, Phase 8 will map control fields to EnergyPlus actuators or
supervisory schedules and apply them before the next interval. No forward injection
or IDF modification is implemented now.

## 15. Latency-management strategy

Agent calls will have a timeout, bounded retries, and a deterministic fallback
schedule. Telemetry will be summarized to the useful horizon rather than sending
every record. Full raw logs will not be included in every prompt. A late response
will be rejected for its expired interval.

## 16. Long-log management

The runtime layer will extract errors, summarize repeated warnings, retain raw logs
on disk, send only relevant excerpts to the LLM, and preserve references to the
full log files for operators and audits.

## 17. Baseline-versus-agent comparison

Official runs must use identical EnergyPlus IDF, EPW, timestep, warm-up, seeds where
applicable, output variables, and evaluation windows. Reports will compare total
kWh, percentage reduction, peak demand, cost/carbon, PMV compliance, IAQ, and
violations. Development outputs remain separate.

## 18. Failure recovery

The coordinator will detect runtime failure, timeout, invalid telemetry, malformed
agent output, validation rejection, and actuator failure. It will record the error,
apply a deterministic safe schedule when possible, stop on unrecoverable
EnergyPlus errors, and surface status without fabricating telemetry.

## 19. IDF versioning

The source baseline will live under `energyplus/models/`. Generated or modified
runtime IDFs will live under `energyplus/models/modified/` with run IDs, timestamps,
input hashes, and provenance. Source IDFs are not globally ignored.

## 20. Audit logging

Each interval will link source telemetry, summarized prompt context, tool calls,
model response, proposed action, validation outcome, applied override, runtime
errors, and resulting telemetry. Logs must make fallback and human intervention
visible. This audit pipeline is planned, not implemented.
