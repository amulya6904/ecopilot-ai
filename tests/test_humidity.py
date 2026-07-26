"""Tests for bounded and seeded humidity behavior."""

import numpy as np

from config.settings import SIMULATOR_PHYSICS
from simulator.humidity import update_humidity_percent


def _update(occupancy: int, compressor: float, seed: int = 1) -> float:
    return update_humidity_percent(
        50, 60, occupancy, 30, compressor, 5, np.random.default_rng(seed)
    )


def test_humidity_effects_and_bounds() -> None:
    result = _update(10, 0.5)
    assert SIMULATOR_PHYSICS.minimum_humidity_percent <= result <= SIMULATOR_PHYSICS.maximum_humidity_percent
    assert _update(0, 1.0) < _update(0, 0.0)
    assert _update(20, 0.0) > _update(0, 0.0)


def test_humidity_is_reproducible() -> None:
    assert _update(10, 0.5, 9) == _update(10, 0.5, 9)
