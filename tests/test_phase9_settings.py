from dataclasses import FrozenInstanceError

import pytest

from safety.settings import SAFETY_SETTINGS, SafetySettings


def test_phase9_limits_are_ordered_and_paths_are_bounded():
    value = SAFETY_SETTINGS
    assert (
        value.emergency_temperature_min_c
        <= value.occupied_temperature_min_c
        < value.occupied_temperature_max_c
        <= value.emergency_temperature_max_c
    )
    assert value.pmv_min < value.pmv_max
    assert value.demand_warning_kw < value.demand_critical_kw
    assert value.minimum_cooling_setpoint_c < value.maximum_cooling_setpoint_c
    assert value.resolve(value.artifact_root).is_relative_to(
        value.repository_root.resolve()
    )


def test_phase9_safety_cannot_be_disabled_or_mutated():
    with pytest.raises(ValueError, match="cannot bypass"):
        SafetySettings(safety_supervisor_enabled=False)
    with pytest.raises(FrozenInstanceError):
        SAFETY_SETTINGS.pmv_min = -1.0
