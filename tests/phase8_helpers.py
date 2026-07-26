from datetime import datetime, timezone

from energyplus.runtime_control.actuator_discovery import ActuatorDescriptor
from energyplus.runtime_control.handles import HandleRegistry
from energyplus.runtime_control.schemas import RuntimeTelemetrySnapshot


ACTUATOR = ActuatorDescriptor(
    "Actuator",
    "Zone Temperature Control",
    "Cooling Setpoint",
    "SPACE1-1",
    "[C]",
)


def telemetry(value: float = 22.0, hour: int = 9) -> RuntimeTelemetrySnapshot:
    return RuntimeTelemetrySnapshot(
        simulation_timestamp=datetime(2013, 1, 1, hour, tzinfo=timezone.utc),
        environment_name="environment-1",
        warmup_flag=False,
        zone_name="SPACE1-1",
        zone_temperature_c=23.0,
        outdoor_temperature_c=30.0,
        current_cooling_setpoint_c=value,
        current_heating_setpoint_c=20.0,
        occupancy=1.0,
        facility_demand_kw=12.0,
        facility_energy_j=100.0,
        handles_ready=True,
    )


def ready_handles() -> HandleRegistry:
    return HandleRegistry(
        zone_temperature=1,
        outdoor_temperature=2,
        cooling_setpoint=3,
        heating_setpoint=4,
        cooling_actuator=5,
        initialized=True,
        api_ready_when_initialized=True,
    )
