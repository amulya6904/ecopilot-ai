"""Validation tests for backend-neutral shared schemas."""

from datetime import datetime
from math import nan

import pytest

from schemas import BuildingState, ControlAction, RuntimeErrorRecord


def _building_state(**overrides) -> BuildingState:
    values = {
        "timestamp": datetime(2026, 7, 25, 9),
        "source": "lightweight",
        "zone_id": "office",
        "zone_name": "Open Office",
        "indoor_temperature_c": 24.0,
        "outdoor_temperature_c": 32.0,
        "occupancy": 10,
        "humidity_percent": 50.0,
        "co2_ppm": 700.0,
        "pmv": None,
        "thermal_comfort_status": "Comfortable",
        "cooling_setpoint_c": 24.0,
        "heating_setpoint_c": None,
        "fan_speed_percent": 50.0,
        "ventilation_level": "medium",
        "hvac_power_kw": 5.0,
        "interval_energy_kwh": 0.4,
        "cumulative_energy_kwh": 1.2,
        "facility_peak_demand_kw": None,
        "electricity_price_per_kwh": 8.0,
        "carbon_intensity_g_per_kwh": 450.0,
    }
    values.update(overrides)
    return BuildingState(**values)


def test_building_state_keeps_unavailable_values_as_none() -> None:
    state = _building_state(pmv=None, co2_ppm=None, facility_peak_demand_kw=None)
    assert state.pmv is None
    assert state.co2_ppm is None
    assert state.facility_peak_demand_kw is None


def test_control_action_supports_baseline_source() -> None:
    action = ControlAction(
        zone_id="office",
        cooling_setpoint_c=22,
        fan_speed_percent=80,
        ventilation_level="medium",
        action_source="baseline_schedule",
        reason="Configured schedule.",
        requested_at=datetime(2026, 7, 25, 9),
        validated=True,
        validation_message="Static configuration.",
    )
    assert action.action_source == "baseline_schedule"
    assert action.validated is True


def test_runtime_error_requires_descriptive_fields() -> None:
    record = RuntimeErrorRecord(
        timestamp=datetime(2026, 7, 25, 9),
        source="energyplus",
        severity="severe",
        code="EPLUS_SEVERE",
        message="Example",
        raw_log_excerpt="Example excerpt",
        recoverable=False,
    )
    assert record.code == "EPLUS_SEVERE"
    with pytest.raises(ValueError, match="required"):
        RuntimeErrorRecord(
            timestamp=datetime(2026, 7, 25, 9),
            source="",
            severity="severe",
            code="E",
            message="Example",
            raw_log_excerpt=None,
            recoverable=False,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"occupancy": -1},
        {"humidity_percent": 101},
        {"interval_energy_kwh": -0.1},
        {"indoor_temperature_c": nan},
    ],
)
def test_invalid_building_numeric_values_are_rejected(overrides) -> None:
    with pytest.raises(ValueError):
        _building_state(**overrides)


def test_invalid_action_numeric_values_are_rejected() -> None:
    with pytest.raises(ValueError):
        ControlAction("office", nan)
    with pytest.raises(ValueError):
        ControlAction("office", 24, fan_speed_percent=101)
    with pytest.raises(ValueError):
        ControlAction("office", 24, confidence=1.1)
