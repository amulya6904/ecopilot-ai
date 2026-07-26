"""Build the one unified safety state consumed by the Phase 9 supervisor."""

from datetime import datetime, timezone

from energyplus.runtime_control.handles import HandleRegistry
from energyplus.runtime_control.schemas import RuntimeTelemetrySnapshot

from .schemas import SafetyHistory, SafetyStateSnapshot


def build_safety_state(
    telemetry: RuntimeTelemetrySnapshot,
    *,
    run_id: str,
    handles: HandleRegistry,
    control_mode: str,
    history: SafetyHistory,
    api_error: bool = False,
    consecutive_agent_failures: int = 0,
    consecutive_actuator_failures: int = 0,
    telemetry_age_seconds: float = 0.0,
    severe_runtime_error: bool = False,
    fatal_runtime_error: bool = False,
) -> SafetyStateSnapshot:
    actions = history.actions
    last = actions[-1] if actions else None
    occupancy = telemetry.occupancy
    return SafetyStateSnapshot(
        run_id=run_id,
        simulation_timestamp=telemetry.simulation_timestamp,
        wall_clock_timestamp=datetime.now(timezone.utc),
        zone_name=telemetry.zone_name,
        display_zone_name="Open Office",
        zone_role="primary_occupied",
        occupied=bool(occupancy is not None and occupancy > 0),
        occupancy_value=occupancy,
        occupancy_source=(
            "EnergyPlusRuntime:Zone People Occupant Count"
            if occupancy is not None
            else "unavailable"
        ),
        indoor_temperature_c=telemetry.zone_temperature_c,
        cooling_setpoint_c=telemetry.current_cooling_setpoint_c,
        heating_setpoint_c=telemetry.current_heating_setpoint_c,
        outdoor_temperature_c=telemetry.outdoor_temperature_c,
        relative_humidity_percent=getattr(
            telemetry, "relative_humidity_percent", None
        ),
        pmv=getattr(telemetry, "pmv", None),
        ppd_percent=getattr(telemetry, "ppd_percent", None),
        facility_demand_kw=telemetry.facility_demand_kw,
        facility_energy_value=telemetry.facility_energy_j,
        telemetry_age_seconds=telemetry_age_seconds,
        handles_ready=handles.ready,
        actuator_valid=handles.cooling_actuator != -1,
        api_error=api_error,
        warmup=telemetry.warmup_flag,
        current_control_mode=control_mode,
        last_action_id=last.action_id if last else None,
        last_action_timestamp=last.timestamp if last else None,
        consecutive_agent_failures=consecutive_agent_failures,
        consecutive_actuator_failures=consecutive_actuator_failures,
        recent_setpoints=[item.setpoint_c for item in actions[-8:]],
        recent_decisions=[item.decision for item in actions[-8:]],
        severe_runtime_error=severe_runtime_error,
        fatal_runtime_error=fatal_runtime_error,
    )


__all__ = ["build_safety_state"]
