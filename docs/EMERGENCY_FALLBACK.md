# Emergency Fallback

Emergency fallback is triggered by an emergency temperature breach, repeated
actuator or agent failures, severe/fatal EnergyPlus errors, an invalid active
actuator, repeated rollback events, or another rule classified as emergency.

The response:

1. reuses the Phase 8 actuator reset;
2. restores the Phase 5 baseline schedule;
3. records the observed restored setpoint when available;
4. persists rollback and/or emergency events;
5. increments failure history;
6. disables further autonomous actions for the run;
7. requires operator acknowledgement.

EnergyPlus is not terminated merely because autonomy is disabled. The runtime is
stopped only when callback/API continuation is unsafe or EnergyPlus reports an
unrecoverable failure.

Rollback reasons are `SETPOINT_APPLICATION_MISMATCH`,
`COMFORT_LIMIT_BREACH`, `PMV_LIMIT_BREACH`,
`DEMAND_CRITICAL_AFTER_ACTION`, `ACTUATOR_VERIFICATION_FAILURE`, and
`RUNTIME_ERROR_AFTER_ACTION`.
