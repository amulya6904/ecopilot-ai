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
