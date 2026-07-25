"""Integration tests for a full conventional baseline run."""

import pandas as pd
import pytest

from config.settings import BASELINE
from config.zones import ZONES
from controllers.baseline import BaselineController, run_baseline_day
from metrics.baseline_metrics import calculate_baseline_summary, calculate_zone_summary
from scripts.run_phase3_baseline import export_baseline_results
from simulator.building import HISTORY_COLUMNS, BuildingSimulator


def _run(seed: int = 42, heat_wave: bool = False) -> pd.DataFrame:
    return run_baseline_day(BuildingSimulator(seed, heat_wave), BaselineController())


def test_full_day_structure_schedule_and_metrics() -> None:
    frame = _run()
    assert len(frame) == 432 and frame["zone_id"].nunique() == 3
    assert set(frame.groupby("zone_id").size()) == {144}
    assert frame["timestamp"].min().strftime("%H:%M") == "08:00"
    assert frame["timestamp"].max().strftime("%H:%M") == "19:55"
    assert not frame.duplicated(["timestamp", "zone_id"]).any()
    assert set(HISTORY_COLUMNS) <= set(frame.columns)
    for time_text, setpoint, fan, ventilation in [
        ("08:00", BASELINE.unoccupied_setpoint_c, BASELINE.unoccupied_fan_speed_percent, BASELINE.unoccupied_ventilation),
        ("09:00", BASELINE.occupied_setpoint_c, BASELINE.occupied_fan_speed_percent, BASELINE.occupied_ventilation),
        ("18:00", BASELINE.unoccupied_setpoint_c, BASELINE.unoccupied_fan_speed_percent, BASELINE.unoccupied_ventilation),
    ]:
        rows = frame[frame["timestamp"].dt.strftime("%H:%M") == time_text]
        assert set(rows["hvac_setpoint_c"]) == {setpoint}
        assert set(rows["fan_speed_percent"]) == {fan}
        assert set(rows["ventilation_level"]) == {ventilation}
    summary = calculate_baseline_summary(frame)
    assert all(summary[key] >= 0 for key in (
        "total_energy_kwh", "total_cost_inr", "total_carbon_kg",
        "peak_hvac_power_kw", "comfort_compliance_percent", "co2_compliance_percent"
    ))
    assert set(calculate_zone_summary(frame)["zone_id"]) == set(ZONES)


def test_reproducibility_heat_wave_and_export(tmp_path) -> None:
    normal = _run()
    assert normal.equals(_run())
    assert not normal.equals(_run(43))
    hot = _run(42, True)
    assert hot["outdoor_temperature_c"].mean() > normal["outdoor_temperature_c"].mean()
    paths = export_baseline_results(normal, calculate_zone_summary(normal), tmp_path)
    assert all(path.exists() for path in paths)
