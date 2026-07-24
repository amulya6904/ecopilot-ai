"""Tests for bounded HVAC energy calculations."""

import pytest

from simulator.energy import calculate_hvac_power_kw, calculate_interval_energy_kwh


def _power(indoor: float = 28, fan: int = 50) -> float:
    return calculate_hvac_power_kw(indoor, 32, 24, fan, 10, 30, 12)


def test_power_is_bounded_and_energy_conversion_is_correct() -> None:
    assert 0 <= _power() <= 12
    assert calculate_interval_energy_kwh(_power(), 5) >= 0
    assert calculate_interval_energy_kwh(6, 5) == pytest.approx(0.5)


def test_demand_and_fan_increase_power() -> None:
    assert _power(fan=90) > _power(fan=30)
    assert _power(indoor=28) > _power(indoor=25)
