# Demand Guardrails

Phase 9 classifies genuine facility demand telemetry as:

| State | Threshold | Policy |
|---|---:|---|
| Normal | below 24 kW | Normal safety rules |
| Warning | 24 kW to below 30 kW | Neutral or demand-reducing direction with comfort headroom |
| Critical | 30 kW or above | Reject demand-increasing cooling action; permit only safe reducing direction |
| Unavailable | no live value | Record uncertainty; make no precise demand claim |

Lowering a cooling setpoint during elevated demand is treated as
demand-increasing direction and rejected. Raising a cooling setpoint is not
assigned a numerical reduction: no validated demand predictor is implemented.

The 24 kW warning and 30 kW critical values are prototype project thresholds
pending final calibration. They are safety guardrails, not final peak-demand
savings evidence.
