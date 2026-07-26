# EnergyPlus Runtime Control

Phase 8 uses the EnergyPlus Python Runtime API against the frozen Phase 5 model and
weather. It discovers and selects exactly:

- component type: `Zone Temperature Control`
- control type: `Cooling Setpoint`
- actuator key: `SPACE1-1`

The control callback is registered after predictor and before HVAC managers. The
observation callback is registered after zone reporting. Required handles are
resolved only after API readiness. Missing optional facility energy, demand,
humidity, PMV, or PPD remains `None`; missing required zone temperature or cooling
setpoint stops control.

There is one `set_actuator_value` location in
`energyplus/runtime_control/callbacks.py`. Reset and rollback reuse
`reset_actuator`; Phase 9 does not duplicate actuator execution.

Applied-action evidence separates the cooling setpoint observed during an override
from the value observed after baseline reset. Every observed applied event receives
`observed_setpoint_after_application` and a tolerance-based `verified` flag.

Phase 8 validates runtime control injection and reset only. It is not a savings or
optimization result.

## Phase 10 complete-horizon use

Phase 10 reuses this exact callback, handle registry, one actuator-write site,
observation linkage, and reset path for an annual controlled evaluation. The
default provider evaluates live EnergyPlus occupancy, `SPACE1-1` temperature,
current cooling setpoint, and facility demand once per simulation hour. It requests
a 0.5°C increase only when the configured demand trigger and measured comfort
headroom both pass. Phase 9 remains final authority.

For quantitative comparison, `run_phase8_runtime(..., generate_csv=True)` invokes
ReadVarsESO with a new RVI bound explicitly to that run's ESO and CSV paths. This
prevents telemetry from being redirected to another run. Default Phase 8
validation behavior is unchanged.
