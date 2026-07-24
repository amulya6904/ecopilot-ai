"""Seeded, zone-specific occupancy schedules."""

from datetime import datetime

import numpy as np


def _hour(timestamp: datetime) -> float:
    return timestamp.hour + timestamp.minute / 60


def _bounded_sample(
    low: int, high: int, capacity: int, rng: np.random.Generator
) -> int:
    """Sample near a schedule midpoint, limiting five-minute volatility."""
    lower = max(0, min(low, capacity))
    upper = max(lower, min(high, capacity))
    if lower == upper:
        return lower
    midpoint = (lower + upper) / 2
    standard_deviation = max((upper - lower) / 6, 0.5)
    return int(np.clip(round(rng.normal(midpoint, standard_deviation)), lower, upper))


def generate_occupancy(
    zone_id: str,
    timestamp: datetime,
    maximum_occupancy: int,
    rng: np.random.Generator,
) -> int:
    """Return occupancy for a five-minute interval using frozen schedules."""
    if maximum_occupancy <= 0:
        raise ValueError("Maximum occupancy must be positive.")
    hour = _hour(timestamp)

    if zone_id == "office":
        if hour < 9:
            bounds = (0, 3)
        elif hour < 10:
            bounds = (8, 18)
        elif hour < 13:
            bounds = (20, 28)
        elif hour < 14:
            bounds = (8, 15)
        elif hour < 17:
            bounds = (18, 27)
        elif hour < 18:
            bounds = (5, 15)
        else:
            bounds = (0, 2)
    elif zone_id == "conference":
        if 10 <= hour < 11:
            bounds = (7, 9)
        elif 14 <= hour < 15:
            bounds = (11, 12)
        elif 16 <= hour < 16.5:
            bounds = (5, 7)
        else:
            bounds = (0, 0)
    elif zone_id == "lab":
        if 9 <= hour < 10.5:
            bounds = (18, 22)
        elif 11 <= hour < 12.5:
            bounds = (13, 17)
        elif 14 <= hour < 16:
            bounds = (21, 25)
        elif 17 <= hour < 18:
            bounds = (8, 12)
        else:
            bounds = (0, 3)
    else:
        raise ValueError(f"Unknown zone ID: {zone_id}")

    return _bounded_sample(*bounds, maximum_occupancy, rng)
