"""Fast and error-aware live telemetry reads from EnergyPlus callbacks."""

from datetime import datetime, timedelta, timezone
from typing import Any

from .handles import HandleRegistry
from .schemas import RuntimeTelemetrySnapshot
from .settings import PHASE8_SETTINGS, Phase8Settings


def simulation_datetime(exchange: Any, state: Any) -> datetime:
    year = int(exchange.calendar_year(state) or exchange.year(state) or 2013)
    if year < 1900:
        year = 2013
    day = max(1, int(exchange.day_of_year(state)))
    hour = int(exchange.hour(state))
    minutes = int(exchange.minutes(state))
    return (
        datetime(year, 1, 1, tzinfo=timezone.utc)
        + timedelta(days=day - 1, hours=hour, minutes=minutes)
    )


def _variable(exchange: Any, state: Any, handle: int) -> float | None:
    if handle == -1:
        return None
    exchange.reset_api_error_flag(state)
    value = float(exchange.get_variable_value(state, handle))
    if value == 0.0 and exchange.api_error_flag(state):
        exchange.reset_api_error_flag(state)
        return None
    return value


def _meter(exchange: Any, state: Any, handle: int) -> float | None:
    if handle == -1:
        return None
    exchange.reset_api_error_flag(state)
    value = float(exchange.get_meter_value(state, handle))
    if value == 0.0 and exchange.api_error_flag(state):
        exchange.reset_api_error_flag(state)
        return None
    return value


def read_runtime_telemetry(
    exchange: Any,
    state: Any,
    registry: HandleRegistry,
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> RuntimeTelemetrySnapshot:
    zone_temperature = _variable(
        exchange, state, registry.zone_temperature
    )
    cooling_setpoint = _variable(
        exchange, state, registry.cooling_setpoint
    )
    heating_setpoint = _variable(
        exchange, state, registry.heating_setpoint
    )
    if zone_temperature is None or cooling_setpoint is None:
        raise RuntimeError("Required EnergyPlus telemetry is unavailable.")
    demand_w = _variable(exchange, state, registry.facility_demand)
    return RuntimeTelemetrySnapshot(
        simulation_timestamp=simulation_datetime(exchange, state),
        environment_name=f"environment-{exchange.current_environment_num(state)}",
        warmup_flag=bool(exchange.warmup_flag(state)),
        zone_name=settings.controlled_zone,
        zone_temperature_c=zone_temperature,
        outdoor_temperature_c=_variable(
            exchange, state, registry.outdoor_temperature
        ),
        current_cooling_setpoint_c=cooling_setpoint,
        current_heating_setpoint_c=heating_setpoint,
        occupancy=_variable(exchange, state, registry.occupancy),
        facility_demand_kw=(demand_w / 1000.0 if demand_w is not None else None),
        facility_energy_j=_meter(exchange, state, registry.facility_energy),
        handles_ready=registry.ready,
        relative_humidity_percent=_variable(
            exchange, state, registry.relative_humidity
        ),
        pmv=_variable(exchange, state, registry.pmv),
        ppd_percent=_variable(exchange, state, registry.ppd),
    )


__all__ = ["read_runtime_telemetry", "simulation_datetime"]
