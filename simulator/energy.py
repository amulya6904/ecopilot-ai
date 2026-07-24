"""Bounded HVAC power and interval-energy calculations."""

from config.settings import SIMULATOR_PHYSICS


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def calculate_hvac_power_kw(
    indoor_temperature_c: float,
    outdoor_temperature_c: float,
    setpoint_c: float,
    fan_speed_percent: int,
    occupancy: int,
    maximum_occupancy: int,
    maximum_hvac_power_kw: float,
) -> float:
    """Calculate HVAC power using thermal, fan, occupancy, and outdoor loads."""
    if not 0 <= fan_speed_percent <= 100:
        raise ValueError("Fan speed must be between zero and 100 percent.")
    if occupancy < 0 or maximum_occupancy <= 0 or occupancy > maximum_occupancy:
        raise ValueError("Occupancy values are invalid.")
    if maximum_hvac_power_kw < 0:
        raise ValueError("Maximum HVAC power cannot be negative.")

    temperature_error = max(indoor_temperature_c - setpoint_c, 0.0)
    compressor_fraction = min(temperature_error / 4.0, 1.0)
    fan_fraction = fan_speed_percent / 100.0
    occupancy_ratio = occupancy / maximum_occupancy
    outdoor_load_ratio = _clamp(
        max(outdoor_temperature_c - setpoint_c, 0.0) / 15.0, 0.0, 1.0
    )
    power_fraction = (
        0.08 * fan_fraction
        + 0.75 * compressor_fraction * fan_fraction
        + 0.10 * occupancy_ratio
        + 0.07 * outdoor_load_ratio
    )
    power_fraction = _clamp(
        power_fraction,
        SIMULATOR_PHYSICS.minimum_hvac_power_fraction,
        SIMULATOR_PHYSICS.maximum_hvac_power_fraction,
    )
    return _clamp(maximum_hvac_power_kw * power_fraction, 0.0, maximum_hvac_power_kw)


def calculate_interval_energy_kwh(power_kw: float, step_minutes: int) -> float:
    """Convert non-negative power to energy for an interval."""
    if power_kw < 0:
        raise ValueError("Power cannot be negative.")
    if step_minutes <= 0:
        raise ValueError("Step duration must be positive.")
    return power_kw * step_minutes / 60.0
