# Closed-Loop Execution

The verified runtime path is:

```text
Phase 7 advisory proposal, manual input, or deterministic mock
  -> strict Phase 8 ExecutableActionCandidate
  -> Phase 9 SafetyStateSnapshot and SafetyDecision
  -> Phase 8 preliminary/revalidation gate
  -> one Phase 8 actuator write or baseline reset
  -> live EnergyPlus observation
  -> Phase 9 post-action verification
  -> continue, rollback, or emergency disablement
```

Agent inference and MCP retrieval do not execute inside EnergyPlus callbacks.
Callbacks perform only bounded local validation, telemetry reads, the one actuator
write/reset, observation linking, and audit updates.

Manual mode proves apply/observe/reset. Mock mode proves multiple hourly intervals,
an intentionally rejected candidate, fallback, and reset. Phase 9 adds a real
clamped-action validation in which the raw out-of-range request is never written;
the nearby safe value is independently checked and then passed to Phase 8.

No lightweight simulation is substituted for a requested EnergyPlus runtime run.
No final baseline-versus-agent comparison is performed.

## Phase 10 annual loop

The final sentence above describes the Phase 8–9 validation boundary. Phase 10 now
adds the separate annual evaluation and comparison workflow:

```text
hourly EnergyPlus evidence
  -> deterministic demand/comfort opportunity
  -> Phase 9 decision
  -> Phase 8 apply or reset
  -> linked observation and post-action verification
  -> continue for the complete annual horizon
  -> normalize and compare only after EnergyPlus exits cleanly
```

The accepted run completed 8,760 hourly reporting intervals, recorded 1,090 safety
decisions and 680 actuator writes, and produced zero rollbacks, severe errors, or
fatal errors. Fallback/reset counts remain visible in reliability artifacts.
