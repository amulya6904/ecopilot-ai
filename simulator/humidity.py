"""Simple bounded humidity model for the Phase 2 simulator."""

import numpy as np

from config.settings import SIMULATOR_PHYSICS


def update_humidity_percent(
    current_humidity_percent: float,
    outdoor_humidity_percent: float,
    occupancy: int,
    maximum_occupancy: int,
    compressor_fraction: float,
    step_minutes: int,
    rng: np.random.Generator,
) -> float:
    """Update indoor relative humidity for one interval."""
    if occupancy < 0 or occupancy > maximum_occupancy:
        raise ValueError("Occupancy values are invalid.")
    if maximum_occupancy <= 0 or step_minutes <= 0:
        raise ValueError("Capacity and step duration must be positive.")
    if not 0 <= compressor_fraction <= 1:
        raise ValueError("Compressor fraction must be between zero and one.")

    interval_hours = step_minutes / 60.0
    occupancy_ratio = occupancy / maximum_occupancy
    outdoor_effect = (
        SIMULATOR_PHYSICS.humidity_outdoor_transfer_per_hour
        * (outdoor_humidity_percent - current_humidity_percent)
        * interval_hours
    )
    occupant_effect = (
        SIMULATOR_PHYSICS.humidity_occupant_gain_per_hour
        * occupancy_ratio
        * interval_hours
    )
    dehumidification_effect = (
        SIMULATOR_PHYSICS.humidity_dehumidification_per_hour
        * compressor_fraction
        * interval_hours
    )
    noise = float(rng.normal(0, SIMULATOR_PHYSICS.humidity_noise_std_percent))
    next_humidity = (
        current_humidity_percent + outdoor_effect + occupant_effect
        - dehumidification_effect + noise
    )
    return float(np.clip(
        next_humidity,
        SIMULATOR_PHYSICS.minimum_humidity_percent,
        SIMULATOR_PHYSICS.maximum_humidity_percent,
    ))
