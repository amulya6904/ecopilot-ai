from dataclasses import replace

import pytest

from energyplus.runtime_control.settings import PHASE8_SETTINGS


def test_phase8_safety_defaults():
    assert PHASE8_SETTINGS.enable_real_llm is False
    assert PHASE8_SETTINGS.maximum_setpoint_change_c == 1.0
    assert PHASE8_SETTINGS.fallback_policy == "phase5_baseline"
    assert PHASE8_SETTINGS.final_savings_result is False


def test_invalid_phase8_bounds_fail():
    with pytest.raises(ValueError):
        replace(
            PHASE8_SETTINGS,
            minimum_cooling_setpoint_c=30,
            maximum_cooling_setpoint_c=20,
        )
