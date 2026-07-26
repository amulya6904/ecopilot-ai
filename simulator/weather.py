"""Seeded outdoor environment generation for the Phase 2 simulator."""

from datetime import datetime

import numpy as np

from config.settings import AIR_QUALITY, SIMULATOR_PHYSICS
from simulator.models import EnvironmentState

_TEMPERATURE_ANCHORS = ((8, 25.0), (10, 28.0), (12, 31.0), (15, 34.0),
                        (18, 29.0), (20, 27.0))
_HUMIDITY_ANCHORS = ((8, 65.0), (12, 52.0), (15, 45.0), (20, 58.0))


def _decimal_hour(timestamp: datetime) -> float:
    return timestamp.hour + timestamp.minute / 60 + timestamp.second / 3600


def _interpolate(anchors: tuple[tuple[int, float], ...], hour: float) -> float:
    hours, values = zip(*anchors)
    return float(np.interp(hour, hours, values))


def generate_environment(
    timestamp: datetime,
    rng: np.random.Generator,
    heat_wave: bool = False,
) -> EnvironmentState:
    """Generate plausible outdoor and grid conditions without external services."""
    hour = _decimal_hour(timestamp)
    temperature = _interpolate(_TEMPERATURE_ANCHORS, hour)
    temperature += float(rng.normal(0, SIMULATOR_PHYSICS.weather_temperature_noise_std_c))
    if heat_wave:
        temperature += 5.0

    humidity = _interpolate(_HUMIDITY_ANCHORS, hour)
    humidity += float(rng.normal(0, SIMULATOR_PHYSICS.weather_humidity_noise_std_percent))
    humidity = float(np.clip(humidity, 0.0, 100.0))

    if hour < 11:
        price, carbon = 7.0, 350.0
    elif hour < 17:
        price, carbon = 10.0, 650.0
    else:
        price, carbon = 8.0, 450.0

    return EnvironmentState(
        timestamp=timestamp,
        outdoor_temperature_c=temperature,
        outdoor_humidity_percent=humidity,
        electricity_price_per_kwh=price,
        carbon_intensity_g_per_kwh=carbon,
        outdoor_co2_ppm=AIR_QUALITY.outdoor_co2_ppm,
    )
