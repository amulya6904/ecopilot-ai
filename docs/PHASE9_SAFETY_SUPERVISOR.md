# Phase 9 Safety Supervisor

Phase 9 adds deterministic safety, comfort, PMV, demand, freshness, rate, and
actuator-health supervision to the verified Phase 8 runtime-control path. PMV is
used only when genuinely available; otherwise the system explicitly uses an
occupied-temperature proxy. This phase validates safety intervention and recovery,
not final optimization or savings.

## Authority and outcomes

The frozen `SafetySettings` object forbids autonomous bypass. The supervisor
accepts only `SafetyStateSnapshot` and `ExecutableActionCandidate`, evaluates rules
in a fixed deterministic order, and returns:

- `approve`
- `approve_with_clamp`
- `hold`
- `reject`
- `fallback`
- `emergency_fallback`

The most severe failed rule controls the result. LLM confidence is only metadata
and cannot override a rule. The controlled zone is the primary occupied,
non-plenum `SPACE1-1`.

## Checks

Checks cover run/zone identity, telemetry presence and freshness, finite and
physically plausible values, warmup, handles, API health, cooling bounds, maximum
delta, energy/comfort direction, unsupported claims, heating/cooling deadband,
hold time, hourly action rate, active conflicts, stale actions, oscillation,
occupancy-aware comfort, genuine PMV/PPD, explicit proxy uncertainty, facility
demand, repeated failures, emergency temperature, and severe/fatal runtime errors.

## Evidence

Each run writes strict state, proposal, rule, decision, clamp/rejection,
post-action, rollback, emergency, fault, runtime-error, configuration, metadata,
and summary artifacts beneath `results/safety/phase9/<run-id>/`. The summary
classification is `safety_supervised_energyplus_runtime_validation`; optimization
and savings flags are always false.
