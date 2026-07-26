"""Stateful simulation of one configured building zone."""

from datetime import datetime

import numpy as np

from config.settings import COMFORT, SIMULATOR_PHYSICS
from config.zones import ZoneConfiguration
from simulator.co2 import update_co2_ppm
from simulator.energy import calculate_hvac_power_kw, calculate_interval_energy_kwh
from simulator.humidity import update_humidity_percent
from simulator.models import EnvironmentState, HVACAction, ZoneRuntime, ZoneState


def comfort_status(temperature_c: float, occupancy: int) -> str:
    """Classify occupied comfort using frozen Phase 1 temperature ranges."""
    if occupancy == 0:
        return "Unoccupied"
    if COMFORT.occupied_preferred_min_c <= temperature_c <= COMFORT.occupied_preferred_max_c:
        return "Comfortable"
    if COMFORT.occupied_allowed_min_c <= temperature_c <= COMFORT.occupied_allowed_max_c:
        return "Acceptable"
    return "Uncomfortable"


class ZoneSimulator:
    """Maintain runtime state and advance a single building zone."""

    def __init__(
        self,
        zone_id: str,
        zone_configuration: ZoneConfiguration,
        rng: np.random.Generator,
        step_minutes: int,
    ) -> None:
        if step_minutes <= 0:
            raise ValueError("Simulation step must be positive.")
        self.zone_id = zone_id
        self.configuration = zone_configuration
        self.rng = rng
        self.step_minutes = step_minutes
        self.runtime = self._initial_runtime()

    def _initial_runtime(self) -> ZoneRuntime:
        return ZoneRuntime(
            zone_id=self.zone_id,
            temperature_c=self.configuration["initial_temperature_c"],
            humidity_percent=self.configuration["initial_humidity_percent"],
            co2_ppm=self.configuration["initial_co2_ppm"],
        )

    def reset(self) -> None:
        """Restore configured physical state; RNG lifecycle is owned by the building."""
        self.runtime = self._initial_runtime()

    def step(
        self,
        timestamp: datetime,
        environment: EnvironmentState,
        occupancy: int,
        action: HVACAction,
    ) -> ZoneState:
        """Advance the zone by one interval and return an immutable record."""
        capacity = self.configuration["maximum_occupancy"]
        if not 0 <= occupancy <= capacity:
            raise ValueError(f"{self.zone_id}: occupancy is outside zone capacity.")

        power_kw = calculate_hvac_power_kw(
            indoor_temperature_c=self.runtime.temperature_c,
            outdoor_temperature_c=environment.outdoor_temperature_c,
            setpoint_c=action.setpoint_c,
            fan_speed_percent=action.fan_speed_percent,
            occupancy=occupancy,
            maximum_occupancy=capacity,
            maximum_hvac_power_kw=self.configuration["maximum_hvac_power_kw"],
        )
        interval_energy = calculate_interval_energy_kwh(power_kw, self.step_minutes)
        temperature_error = max(self.runtime.temperature_c - action.setpoint_c, 0.0)
        compressor_fraction = min(temperature_error / 4.0, 1.0)
        interval_hours = self.step_minutes / 60.0
        occupancy_ratio = occupancy / capacity
        outdoor_effect = (
            SIMULATOR_PHYSICS.outdoor_heat_transfer_per_hour
            * (environment.outdoor_temperature_c - self.runtime.temperature_c)
            * interval_hours
        )
        occupant_effect = (
            SIMULATOR_PHYSICS.occupant_heat_gain_c_per_hour
            * occupancy_ratio
            * interval_hours
        )
        equipment_effect = (
            SIMULATOR_PHYSICS.equipment_heat_gains[
                self.configuration["equipment_heat_level"]
            ]
            * interval_hours
        )
        fan_fraction = action.fan_speed_percent / 100.0
        cooling_effect = (
            SIMULATOR_PHYSICS.cooling_effect_c_per_hour
            * compressor_fraction
            * fan_fraction
            * interval_hours
        )
        noise = float(self.rng.normal(
            0, SIMULATOR_PHYSICS.temperature_noise_std_c
        ))
        next_temperature = float(np.clip(
            self.runtime.temperature_c + outdoor_effect + occupant_effect
            + equipment_effect - cooling_effect + noise,
            SIMULATOR_PHYSICS.minimum_temperature_c,
            SIMULATOR_PHYSICS.maximum_temperature_c,
        ))
        next_humidity = update_humidity_percent(
            self.runtime.humidity_percent,
            environment.outdoor_humidity_percent,
            occupancy,
            capacity,
            compressor_fraction,
            self.step_minutes,
            self.rng,
        )
        next_co2 = update_co2_ppm(
            self.runtime.co2_ppm,
            environment.outdoor_co2_ppm,
            occupancy,
            self.configuration["area_m2"],
            action.ventilation_level,
            self.step_minutes,
        )
        cumulative_energy = self.runtime.cumulative_energy_kwh + interval_energy
        self.runtime = ZoneRuntime(
            zone_id=self.zone_id,
            temperature_c=next_temperature,
            humidity_percent=next_humidity,
            co2_ppm=next_co2,
            cumulative_energy_kwh=cumulative_energy,
        )
        return ZoneState(
            timestamp=timestamp,
            zone_id=self.zone_id,
            zone_name=self.configuration["name"],
            indoor_temperature_c=next_temperature,
            outdoor_temperature_c=environment.outdoor_temperature_c,
            humidity_percent=next_humidity,
            occupancy=occupancy,
            co2_ppm=next_co2,
            hvac_setpoint_c=action.setpoint_c,
            fan_speed_percent=action.fan_speed_percent,
            ventilation_level=action.ventilation_level,
            hvac_power_kw=power_kw,
            interval_energy_kwh=interval_energy,
            cumulative_energy_kwh=cumulative_energy,
            comfort_status=comfort_status(next_temperature, occupancy),
            electricity_price_per_kwh=environment.electricity_price_per_kwh,
            carbon_intensity_g_per_kwh=environment.carbon_intensity_g_per_kwh,
        )
