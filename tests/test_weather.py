"""Tests for deterministic outdoor environment generation."""

from datetime import datetime

import numpy as np

from simulator.weather import generate_environment


def test_environment_values_and_daily_shape() -> None:
    morning = generate_environment(datetime(2026, 7, 25, 8), np.random.default_rng(1))
    afternoon = generate_environment(datetime(2026, 7, 25, 15), np.random.default_rng(1))
    assert afternoon.outdoor_temperature_c > morning.outdoor_temperature_c
    assert 0 <= morning.outdoor_humidity_percent <= 100
    assert morning.electricity_price_per_kwh > 0
    assert morning.carbon_intensity_g_per_kwh > 0
    assert 15 <= morning.outdoor_temperature_c <= 45


def test_heat_wave_adds_five_degrees() -> None:
    timestamp = datetime(2026, 7, 25, 12)
    normal = generate_environment(timestamp, np.random.default_rng(2))
    hot = generate_environment(timestamp, np.random.default_rng(2), heat_wave=True)
    assert hot.outdoor_temperature_c == normal.outdoor_temperature_c + 5
    assert hot.electricity_price_per_kwh == normal.electricity_price_per_kwh


def test_weather_is_reproducible() -> None:
    timestamp = datetime(2026, 7, 25, 10)
    assert generate_environment(timestamp, np.random.default_rng(4)) == generate_environment(
        timestamp, np.random.default_rng(4)
    )
