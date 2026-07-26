"""Regression tests for the lightweight simulator adapter."""

import pytest

from backends.lightweight import LightweightSimulatorBackend
from schemas import ControlAction


def test_full_day_preserves_structure_source_and_unavailable_pmv() -> None:
    backend = LightweightSimulatorBackend(random_seed=42)
    frame = backend.run_full_day()
    assert backend.backend_name == "lightweight"
    assert backend.data_source_label == "Lightweight Development Simulator"
    assert backend.is_available is True
    assert len(frame) == 432
    assert frame["zone_id"].nunique() == 3
    assert set(frame.groupby("zone_id").size()) == {144}
    assert set(frame["source"]) == {"lightweight"}
    assert frame["pmv"].isna().all()
    assert frame["facility_peak_demand_kw"].isna().all()
    assert backend.get_runtime_errors() == []


def test_seed_reset_and_heat_wave_behavior_are_preserved() -> None:
    first_backend = LightweightSimulatorBackend(random_seed=42)
    first = first_backend.run_full_day()
    second = LightweightSimulatorBackend(random_seed=42).run_full_day()
    assert first.equals(second)
    first_backend.reset()
    assert first.equals(first_backend.run_full_day())
    hot = LightweightSimulatorBackend(random_seed=42, heat_wave=True).run_full_day()
    assert hot["outdoor_temperature_c"].mean() == pytest.approx(
        first["outdoor_temperature_c"].mean() + 5
    )


def test_shared_control_action_is_converted_without_rewriting_simulator() -> None:
    backend = LightweightSimulatorBackend(random_seed=7)
    state = backend.step({
        "office": ControlAction(
            zone_id="office",
            cooling_setpoint_c=23,
            fan_speed_percent=70,
            ventilation_level="high",
            action_source="fixed_test_action",
        )
    })
    office = next(record for record in state if record.zone_id == "office")
    assert office.cooling_setpoint_c == 23
    assert office.fan_speed_percent == 70
    assert office.ventilation_level == "high"
    assert office.source == "lightweight"
