"""End-to-end tests for the multi-zone orchestrator."""

import pandas as pd
import pytest

from config.settings import SIMULATION
from config.zones import ZONES
from simulator.building import HISTORY_COLUMNS, BuildingSimulator
from simulator.models import HVACAction


def test_full_day_contract_and_bounds() -> None:
    simulator = BuildingSimulator(42)
    assert len(simulator.zones) == 3
    frame = simulator.run_full_day()
    assert len(frame) == 432
    assert set(frame.groupby("zone_id").size()) == {144}
    assert frame["timestamp"].min().strftime("%H:%M") == "08:00"
    assert frame["timestamp"].max().strftime("%H:%M") == "19:55"
    assert not frame.duplicated(["timestamp", "zone_id"]).any()
    assert list(frame.columns) == HISTORY_COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(frame["timestamp"])
    assert (frame["interval_energy_kwh"] >= 0).all()
    for zone_id, configuration in ZONES.items():
        rows = frame[frame["zone_id"] == zone_id]
        assert (rows["occupancy"] <= configuration["maximum_occupancy"]).all()
        assert (rows["hvac_power_kw"] <= configuration["maximum_hvac_power_kw"]).all()


def test_seed_and_reset_reproducibility() -> None:
    first = BuildingSimulator(42).run_full_day()
    second = BuildingSimulator(42).run_full_day()
    assert first.equals(second)
    assert not first.equals(BuildingSimulator(43).run_full_day())
    simulator = BuildingSimulator(42)
    original = simulator.run_full_day()
    simulator.reset()
    assert original.equals(simulator.run_full_day())


def test_actions_completion_and_heat_wave() -> None:
    simulator = BuildingSimulator()
    with pytest.raises(ValueError, match="Unknown action"):
        simulator.step({"lobby": HVACAction(24, 50, "medium")})
    custom = {"office": HVACAction(23, 70, "high")}
    assert simulator.step(custom)[0].timestamp == simulator.start_timestamp
    simulator.run_full_day()
    assert simulator.is_complete
    with pytest.raises(RuntimeError, match="complete"):
        simulator.step()
    normal = BuildingSimulator(42).run_full_day()
    hot = BuildingSimulator(42, heat_wave=True).run_full_day()
    assert hot["outdoor_temperature_c"].mean() == pytest.approx(
        normal["outdoor_temperature_c"].mean() + 5
    )
    assert SIMULATION.total_steps == 144
