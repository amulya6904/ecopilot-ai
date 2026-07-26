"""Tests for CO2 generation and removal."""

import pytest

from config.settings import SIMULATOR_PHYSICS
from simulator.co2 import update_co2_ppm


def _update(occupancy: int, ventilation: str, current: float = 900) -> float:
    return update_co2_ppm(current, 420, occupancy, 100, ventilation, 5)


def test_occupancy_and_ventilation_behavior() -> None:
    assert _update(20, "medium") > _update(2, "medium")
    assert _update(10, "high") < _update(10, "low")
    assert 420 <= _update(0, "medium") < 900
    assert _update(10000, "low") <= SIMULATOR_PHYSICS.maximum_co2_ppm


def test_invalid_ventilation_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid ventilation"):
        _update(1, "turbo")
