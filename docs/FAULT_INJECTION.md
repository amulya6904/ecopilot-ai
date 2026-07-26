# Phase 9 Fault Injection

Run:

```powershell
python -m scripts.run_phase9_fault_injection
```

The deterministic suite covers 22 cases: unknown zone, plenum, out-of-range
setpoint, excessive delta, deadband, stale/missing telemetry, PMV unavailable,
PMV hot, PPD warning, demand warning/critical, wrong energy direction, minimum
hold, action rate, oscillation, invalid actuator, write mismatch, repeated agent
and actuator failures, and severe runtime error.

Every case defines an expected outcome and rule code. The command prints one
pass/fail line per case and exits non-zero on any mismatch. Results are written to
the Phase 9 artifact bundle and exercised by normal unit tests without requiring
EnergyPlus or Ollama.
