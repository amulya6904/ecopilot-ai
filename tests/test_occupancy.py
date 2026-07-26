"""Tests for zone-specific occupancy schedules."""

from datetime import datetime

import numpy as np
import pytest

from simulator.occupancy import generate_occupancy


def _occupancy(zone: str, hour: int, minute: int, capacity: int, seed: int = 1) -> int:
    return generate_occupancy(
        zone, datetime(2026, 7, 25, hour, minute), capacity, np.random.default_rng(seed)
    )


def test_schedule_ranges_and_capacity() -> None:
    for zone, capacity in (("office", 30), ("conference", 12), ("lab", 25)):
        for hour in range(8, 20):
            value = _occupancy(zone, hour, 0, capacity, hour)
            assert 0 <= value <= capacity
    assert _occupancy("office", 11, 0, 30) > _occupancy("office", 8, 0, 30)
    assert _occupancy("conference", 10, 15, 12) > 0
    assert _occupancy("conference", 12, 0, 12) == 0
    assert _occupancy("lab", 14, 0, 25) > 0


def test_occupancy_is_reproducible_and_rejects_unknown_zone() -> None:
    assert _occupancy("lab", 9, 30, 25, 8) == _occupancy("lab", 9, 30, 25, 8)
    with pytest.raises(ValueError, match="Unknown zone"):
        _occupancy("lobby", 10, 0, 5)
