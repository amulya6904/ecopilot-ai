"""Backend-neutral building telemetry records."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.models import ZoneState


def _require_finite(name: str, value: float | None) -> None:
    if value is not None and not isfinite(value):
        raise ValueError(f"{name} must be finite when provided.")


@dataclass(frozen=True)
class BuildingState:
    """One zone's telemetry for one backend control interval.

    Optional fields represent genuinely unavailable telemetry. In particular,
    the lightweight simulator does not calculate PMV.
    """

    timestamp: datetime
    source: str
    zone_id: str
    zone_name: str
    indoor_temperature_c: float
    outdoor_temperature_c: float
    occupancy: int
    humidity_percent: float
    co2_ppm: float | None
    pmv: float | None
    thermal_comfort_status: str
    cooling_setpoint_c: float
    heating_setpoint_c: float | None
    fan_speed_percent: float | None
    ventilation_level: str | None
    hvac_power_kw: float
    interval_energy_kwh: float
    cumulative_energy_kwh: float
    facility_peak_demand_kw: float | None
    electricity_price_per_kwh: float
    carbon_intensity_g_per_kwh: float

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime.")
        if not self.source.strip() or not self.zone_id.strip() or not self.zone_name.strip():
            raise ValueError("source, zone_id, and zone_name are required.")
        if not self.thermal_comfort_status.strip():
            raise ValueError("thermal_comfort_status is required.")
        if self.occupancy < 0:
            raise ValueError("occupancy must not be negative.")
        if not 0 <= self.humidity_percent <= 100:
            raise ValueError("humidity_percent must be between 0 and 100.")
        if self.co2_ppm is not None and self.co2_ppm <= 0:
            raise ValueError("co2_ppm must be positive when provided.")
        if self.fan_speed_percent is not None and not 0 <= self.fan_speed_percent <= 100:
            raise ValueError("fan_speed_percent must be between 0 and 100.")
        nonnegative = {
            "hvac_power_kw": self.hvac_power_kw,
            "interval_energy_kwh": self.interval_energy_kwh,
            "cumulative_energy_kwh": self.cumulative_energy_kwh,
            "electricity_price_per_kwh": self.electricity_price_per_kwh,
            "carbon_intensity_g_per_kwh": self.carbon_intensity_g_per_kwh,
        }
        if any(value < 0 for value in nonnegative.values()):
            raise ValueError("Power, energy, price, and carbon values cannot be negative.")
        if self.facility_peak_demand_kw is not None and self.facility_peak_demand_kw < 0:
            raise ValueError("facility_peak_demand_kw cannot be negative.")
        for name in (
            "indoor_temperature_c",
            "outdoor_temperature_c",
            "humidity_percent",
            "co2_ppm",
            "pmv",
            "cooling_setpoint_c",
            "heating_setpoint_c",
            "fan_speed_percent",
            "hvac_power_kw",
            "interval_energy_kwh",
            "cumulative_energy_kwh",
            "facility_peak_demand_kw",
            "electricity_price_per_kwh",
            "carbon_intensity_g_per_kwh",
        ):
            _require_finite(name, getattr(self, name))


def from_lightweight_zone_state(state: "ZoneState") -> BuildingState:
    """Convert an existing simulator ``ZoneState`` without inventing telemetry."""

    return BuildingState(
        timestamp=state.timestamp,
        source="lightweight",
        zone_id=state.zone_id,
        zone_name=state.zone_name,
        indoor_temperature_c=state.indoor_temperature_c,
        outdoor_temperature_c=state.outdoor_temperature_c,
        occupancy=state.occupancy,
        humidity_percent=state.humidity_percent,
        co2_ppm=state.co2_ppm,
        pmv=None,
        thermal_comfort_status=state.comfort_status,
        cooling_setpoint_c=state.hvac_setpoint_c,
        heating_setpoint_c=None,
        fan_speed_percent=float(state.fan_speed_percent),
        ventilation_level=state.ventilation_level,
        hvac_power_kw=state.hvac_power_kw,
        interval_energy_kwh=state.interval_energy_kwh,
        cumulative_energy_kwh=state.cumulative_energy_kwh,
        facility_peak_demand_kw=None,
        electricity_price_per_kwh=state.electricity_price_per_kwh,
        carbon_intensity_g_per_kwh=state.carbon_intensity_g_per_kwh,
    )
