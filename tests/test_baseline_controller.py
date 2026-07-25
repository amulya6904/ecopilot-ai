"""Tests for the fixed-schedule conventional controller."""

from datetime import datetime
import inspect

import pytest

from config.settings import BASELINE
from config.zones import ZONES
from controllers.baseline import BaselineController


@pytest.mark.parametrize(
    ("hour", "minute", "occupied"),
    [(8, 0, False), (8, 55, False), (9, 0, True), (17, 55, True),
     (18, 0, False), (19, 55, False)],
)
def test_schedule_boundaries(hour: int, minute: int, occupied: bool) -> None:
    controller = BaselineController()
    action = controller.action_for(datetime(2026, 7, 25, hour, minute), "office")
    if occupied:
        assert action.setpoint_c == BASELINE.occupied_setpoint_c
        assert action.fan_speed_percent == BASELINE.occupied_fan_speed_percent
        assert action.ventilation_level == BASELINE.occupied_ventilation
    else:
        assert action.setpoint_c == BASELINE.unoccupied_setpoint_c
        assert action.fan_speed_percent == BASELINE.unoccupied_fan_speed_percent
        assert action.ventilation_level == BASELINE.unoccupied_ventilation


def test_all_zones_unknown_zone_and_sensor_free_signature() -> None:
    controller = BaselineController()
    assert set(controller.actions_for_building(datetime(2026, 7, 25, 10))) == set(ZONES)
    with pytest.raises(ValueError, match="lobby"):
        controller.action_for(datetime(2026, 7, 25, 10), "lobby")
    assert list(inspect.signature(controller.action_for).parameters) == [
        "timestamp", "zone_id"
    ]
