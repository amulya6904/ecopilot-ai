"""Dataclasses shared by Phase 2 simulator components."""

from dataclasses import dataclass
from datetime import datetime

from config.settings import HVAC


@dataclass(frozen=True)
class HVACAction:
    """Externally supplied HVAC action for one simulation interval."""

    setpoint_c: float
    fan_speed_percent: int
    ventilation_level: str

    def __post_init__(self) -> None:
        if not HVAC.minimum_setpoint_c <= self.setpoint_c <= HVAC.maximum_setpoint_c:
            raise ValueError("HVAC setpoint is outside configured limits.")
        if not (HVAC.minimum_fan_speed_percent <= self.fan_speed_percent
                <= HVAC.maximum_fan_speed_percent):
            raise ValueError("HVAC fan speed is outside configured limits.")
        if self.ventilation_level not in HVAC.ventilation_candidates:
            raise ValueError("HVAC ventilation level is invalid.")


@dataclass(frozen=True)
class EnvironmentState:
    """Outdoor and grid conditions for one interval."""

    timestamp: datetime
    outdoor_temperature_c: float
    outdoor_humidity_percent: float
    electricity_price_per_kwh: float
    carbon_intensity_g_per_kwh: float
    outdoor_co2_ppm: float


@dataclass
class ZoneRuntime:
    """Mutable current physical state for one zone."""

    zone_id: str
    temperature_c: float
    humidity_percent: float
    co2_ppm: float
    cumulative_energy_kwh: float = 0.0


@dataclass(frozen=True)
class ZoneState:
    """Immutable historical record for one zone and interval."""

    timestamp: datetime
    zone_id: str
    zone_name: str
    indoor_temperature_c: float
    outdoor_temperature_c: float
    humidity_percent: float
    occupancy: int
    co2_ppm: float
    hvac_setpoint_c: float
    fan_speed_percent: int
    ventilation_level: str
    hvac_power_kw: float
    interval_energy_kwh: float
    cumulative_energy_kwh: float
    comfort_status: str
    electricity_price_per_kwh: float
    carbon_intensity_g_per_kwh: float
