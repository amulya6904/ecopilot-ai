"""Simple occupancy-generation and ventilation-removal CO2 model."""

from config.settings import SIMULATOR_PHYSICS


def update_co2_ppm(
    current_co2_ppm: float,
    outdoor_co2_ppm: float,
    occupancy: int,
    area_m2: float,
    ventilation_level: str,
    step_minutes: int,
) -> float:
    """Update zone CO2 concentration for one interval."""
    removals = SIMULATOR_PHYSICS.ventilation_removal_fractions
    if ventilation_level not in removals:
        raise ValueError(f"Invalid ventilation level: {ventilation_level}")
    if occupancy < 0:
        raise ValueError("Occupancy cannot be negative.")
    if area_m2 <= 0 or step_minutes <= 0:
        raise ValueError("Area and step duration must be positive.")

    generation_ppm = (
        occupancy
        * SIMULATOR_PHYSICS.co2_generation_factor
        * step_minutes
        * (50.0 / area_m2)
    )
    next_co2 = (
        outdoor_co2_ppm
        + (current_co2_ppm - outdoor_co2_ppm)
        * (1.0 - removals[ventilation_level])
        + generation_ppm
    )
    return max(outdoor_co2_ppm, min(next_co2, SIMULATOR_PHYSICS.maximum_co2_ppm))
