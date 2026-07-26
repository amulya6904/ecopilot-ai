# Phase 8 Safety Gate

Phase 8 retains its deterministic runtime validator for candidate freshness,
identity, bounds, delta, deadband, permissions, and handle readiness. Phase 9 is
the final supervisory authority before the Phase 8 actuator layer.

An executable candidate must have:

- the live run ID and `SPACE1-1` identity;
- the selected cooling-setpoint actuator identifier;
- a current value matching live telemetry;
- a bounded effective and expiration window;
- structured provenance and evidence references.

Raw Phase 7 output is first parsed and deterministically normalized. It cannot
reach `set_actuator_value`. A Phase 9 clamp is recorded with requested and approved
values, rule evidence, and reason, then revalidated by Phase 8 before application.
Hold, reject, fallback, and emergency fallback never write the candidate value.

The single reset path restores the Phase 5 schedule. Callback/API failures also
reset before the simulation is stopped.
