# EcoPilot AI project scope

## Goal and positioning

EcoPilot AI demonstrates an EnergyPlus-first smart-building control architecture
that combines local advisory intelligence with deterministic final authority,
real runtime actuator injection, fault recovery, and reproducible evidence.

The official result is a conservative single-zone proof of concept. It is not a
calibrated real-building deployment, a whole-building optimizer, or a
production safety-certified controller.

## Completed implementation

| Phase | Scope | Classification |
|---|---|---|
| 1 | Configuration and architecture foundation | Configuration |
| 2 | Lightweight development simulator | Development only |
| 3 | Lightweight fixed-schedule benchmark | Development only |
| 4 | EnergyPlus integration | Official execution path |
| 5 | Annual fixed-schedule EnergyPlus baseline | Official EnergyPlus baseline |
| 6 | Bounded local MCP tools | Verified local MCP |
| 7 | qwen3:4b advisory agent | Advisory only |
| 8 | Runtime actuator discovery and injection | Official EnergyPlus controlled evidence |
| 9 | Deterministic safety and fault recovery | Safety validation |
| 10 | Compatible annual quantitative comparison | Official EnergyPlus comparison |
| 11 | Dashboard, documents, demo, and packaging | Submission presentation |

The lightweight simulator validates interfaces and development behavior. Its
outputs are never used for the official savings claim.

## Retained EnergyPlus experiment

The model contains `SPACE1-1` through `SPACE5-1` and `PLENUM-1`. The controlled
experiment changes only the `SPACE1-1` cooling-setpoint actuator:

```text
Zone Temperature Control | Cooling Setpoint | SPACE1-1
```

The Phase 5 baseline and Phase 10 controlled experiment retain the same derived
IDF, EPW, EnergyPlus version, annual period, schedules, occupancy, internal
loads, output requests, and hourly reporting. All 8,760 facility intervals and
52,560 zone records align.

## Architecture boundary

```text
EnergyPlus → telemetry → MCP evidence → local qwen3:4b advisory
           → typed validation → Phase 9 safety → actuator
           → observation → fallback/rollback → comparison
```

The LLM has no direct actuator authority. Local inference remains outside
EnergyPlus callbacks because latency depends on hardware. The official Phase 10
annual result uses a deterministic reproducible policy through the same safety
and actuator boundaries.

## Safety and comfort scope

The Phase 9 supervisor owns comfort, demand, bounds, deadband, freshness,
rate-limit, oscillation, actuator-health, rollback, and emergency-fallback
decisions. Twenty-two of twenty-two fault scenarios pass with all six outcomes
exercised and zero severe/fatal errors.

Genuine PMV/PPD is unavailable from the retained People objects. The system
explicitly uses occupied-temperature compliance as its comfort proxy. Prototype
demand thresholds require site calibration before any deployment.

## Preserved measured result

The official reproducible comparison records:

- baseline facility electricity: `58,568.21190808615 kWh`;
- controlled facility electricity: `58,562.58583227383 kWh`;
- reduction: `5.626075812324416 kWh` (`0.009606022839067856%`);
- occupied-temperature proxy change: `+0.16718913270637614` percentage points;
- peak demand: essentially unchanged;
- severe/fatal errors: `0 / 0`.

The small whole-building effect is consistent with conservative control of one
zone. Cost and carbon are derived from INR 8/kWh and 708 g CO₂/kWh configured
assumptions.

## Out of scope

- physical IoT and direct connection to an occupied building;
- cloud deployment, mobile apps, authentication, Kafka, or Kubernetes;
- production security or safety certification;
- calibrated tariffs, carbon forecasts, or site demand limits;
- multi-zone optimal control;
- fabricated PMV or enlarged savings claims;
- replacing deterministic control authority with an LLM.

## Future work

Future phases may add coordinated multi-zone control, EnergyPlus People inputs
that expose native PMV/PPD, additional buildings and weather years, site
calibration, faster local inference hardware, and a read-only building
management system shadow pilot.
