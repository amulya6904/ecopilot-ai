# EcoPilot AI — Updated Project Scope

## Goal and official positioning

EcoPilot AI is a safe smart-building platform intended to reduce HVAC energy and
carbon impact while maintaining thermal comfort and indoor air quality.

EnergyPlus is the required primary final simulation engine. The final official
baseline and the final AI-controlled run must both be generated through EnergyPlus
under identical IDF and EPW conditions.

The current custom simulator is a Lightweight Development Simulator and fallback
backend. It validates control interfaces, data pipelines, metrics, reproducibility,
and UI behavior before EnergyPlus is connected. It is not a calibrated replacement
for EnergyPlus and its results are not official savings evidence.

## Official target capabilities

The final system requires:

- EnergyPlus zone temperature, energy, occupancy, supported indoor-air-quality,
  PMV/thermal-comfort, and peak-demand telemetry;
- reasoning against energy targets, comfort constraints, peak demand, and carbon
  intensity;
- an open-source LLM cognitive engine such as Qwen, Mistral, or Llama;
- MCP or equivalent bounded agentic tools, including relevant runtime-error and log
  access;
- structured control proposals and automatic forward injection of validated
  setpoints or supervisory overrides into EnergyPlus;
- a quantitative EnergyPlus baseline-versus-agent comparison showing percentage
  kWh reduction while preserving comfort;
- base and modified IDFs, source code, dashboard, architecture documentation,
  presentation, and a demonstration video of at most three minutes.

EnergyPlus batch execution and the official fixed-schedule baseline are implemented
in Phases 4–5. Phase 6 implements bounded MCP access, Phase 7 implements the local
advisory LLM, Phase 8 implements verified Runtime API actuator control, and Phase 9
implements deterministic safety and recovery. The Phase 10 matched savings
comparison is not implemented.

## Building and development scope

The development harness contains:

1. Open Office (`office`)
2. Conference Room (`conference`)
3. Computer Lab (`lab`)

It models seeded weather, heat waves, occupancy, temperature, humidity, CO2, HVAC
power, interval and cumulative energy, tariff, carbon intensity, and
temperature-based comfort at five-minute intervals. A full day contains 144
intervals and 432 zone records.

Phase 3 applies a fixed occupied/unoccupied schedule and reports development-only
energy, cost, carbon, comfort, CO2, demand, and zone summaries. It makes no savings
claim.

Out of scope for the initial prototype remain physical IoT hardware, cloud
deployment, mobile apps, authentication, reinforcement learning, production-grade
security, Kafka, Kubernetes, and large multi-floor models.

## Target architecture

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

`backends/energyplus.py` will become the primary application-facing EnergyPlus
adapter. The existing `energyplus_adapter/` package is preserved as an earlier
integration boundary.

## Safety principle

**The LLM may propose or request control actions, but every action must pass through
a deterministic validation layer before being applied.**

Safety constraints and operator overrides take precedence over optimization. The
LLM cannot bypass validation or write actuators directly.

## Official evaluation priorities

- System integration: 30%
- Energy efficiency: 25%
- Thermal comfort and constraints: 20%
- Agentic autonomy and code elegance: 15%
- Presentation and documentation: 10%

## Development order

1. Requirements and configuration
2. Lightweight simulator
3. Development baseline
4. EnergyPlus integration
5. EnergyPlus baseline
6. MCP tools
7. Open-source LLM agent
8. Closed-loop execution
9. Safety and comfort validation
10. Quantitative comparison
11. Final dashboard
12. Documentation and submission

Phases 1–9 are complete under their stated classifications. Phase 5 establishes the
official fixed-schedule EnergyPlus baseline using the existing verified EnergyPlus
example model. Original EnergyPlus zone identifiers are preserved, while display
aliases are used for presentation. This phase does not implement MCP, an open-source
LLM, actuator injection, autonomous control, optimization, or savings comparison.

The retained model contains `SPACE1-1` through `SPACE5-1` and `PLENUM-1`.
Configuration maps those identifiers to Open Office, Conference Room, Computer Lab,
Support Zone, Auxiliary Zone, and HVAC Plenum. The plenum remains in raw telemetry
but is excluded from occupied comfort metrics. Existing People, Lights,
ElectricEquipment, ventilation, geometry, sizing, and HVAC availability schedules
are frozen for future comparison.

## Implemented Phase 6 boundary

Phase 6 exposes the verified EnergyPlus and official baseline capabilities through a local MCP server. The server provides bounded, validated tools and read-only resources. It does not yet include an open-source LLM, autonomous reasoning, actuator injection, optimization, or closed-loop control.

The official-SDK stdio server provides discovery, status, baseline artifact, zone,
facility, comfort, thermostat-adherence, diagnostics, and one controlled official
baseline-run tool. Callers cannot select paths, commands, executables, models,
weather files, output locations, or environment values. Phase 7 is the next
handoff for open-source LLM integration.

## Implemented Phase 7 boundary

Phase 7 connects a local open-source LLM to the verified Phase 6 MCP tool layer.
Its output remains advisory. Phases 8–9 separately own executable-candidate
conversion, deterministic safety authority, runtime application, observation,
fallback, and recovery. Optimization results and savings comparison remain
unimplemented.

The model sees 12 read-only allowlisted tools. Strict schemas and an independent
validator check zone identity, comfort eligibility, configured bounds, maximum
change, heating deadband, retrieved current setpoint, evidence, occupancy source,
and PMV availability.

## Implemented Phase 8 and Phase 9 boundaries

Phase 8 owns the one verified EnergyPlus cooling-setpoint actuator for `SPACE1-1`,
its callback registration, application/reset behavior, and runtime evidence.
Phase 9 is the mandatory deterministic authority over every executable Phase 8
candidate. It supervises identity, freshness, telemetry health, comfort, genuine
PMV/PPD when available, explicit temperature proxy otherwise, demand, bounds,
deadband, hold/rate, oscillation, actuator health, post-action response, rollback,
and emergency disablement.

Phase 9 adds deterministic safety, comfort, PMV, demand, freshness, rate, and
actuator-health supervision to the verified Phase 8 runtime-control path. PMV is
used only when genuinely available; otherwise the system explicitly uses an
occupied-temperature proxy. This phase validates safety intervention and recovery,
not final optimization or savings.

Phase 10 matched baseline-versus-agent comparison, percentage savings, final
optimization, cost/carbon savings, and annual optimized results remain out of
scope and unimplemented.
