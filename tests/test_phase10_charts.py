import pandas as pd

from comparison.charts import build_chart_figures, write_charts


def test_required_charts_have_units_and_export(tmp_path):
    timestamps = ["2000-01-01T01:00:00", "2000-01-01T02:00:00"]
    energy = pd.DataFrame({
        "timestamp": timestamps,
        "baseline_energy_kwh": [1, 2],
        "controlled_energy_kwh": [1, 1],
        "baseline_cumulative_energy_kwh": [1, 3],
        "controlled_cumulative_energy_kwh": [1, 2],
    })
    demand = pd.DataFrame({
        "timestamp": timestamps,
        "baseline_demand_kw": [1, 2],
        "controlled_demand_kw": [1, 1],
    })
    comfort = pd.DataFrame({
        "timestamp": timestamps,
        "occupancy_controlled": [1, 1],
        "indoor_temperature_c_baseline": [22, 23],
        "indoor_temperature_c_controlled": [22, 23],
        "comfort_min_c": [22, 22],
        "comfort_max_c": [25, 25],
        "cooling_setpoint_c_baseline": [22, 22],
        "cooling_setpoint_c_controlled": [22.5, 22.5],
    })
    cost = pd.DataFrame({
        "timestamp": timestamps, "baseline_cost": [1, 2],
        "controlled_cost": [1, 1],
    })
    carbon = pd.DataFrame({
        "timestamp": timestamps, "baseline_carbon_kg": [1, 2],
        "controlled_carbon_kg": [1, 1],
    })
    actions = pd.DataFrame({
        "timestamp": timestamps,
        "requested_setpoint_c": [22.5, 22.5],
        "approved_setpoint_c": [22.5, 22.5],
        "applied_setpoint_c": [22.5, 22.5],
        "observed_setpoint_c": [22.5, 22.5],
        "fallback": [False, True],
        "rollback": [False, False],
    })
    figures = build_chart_figures(
        energy=energy, demand=demand, comfort=comfort, cost=cost,
        carbon=carbon, actions=actions,
        reliability={}, safety={},
    )
    paths = write_charts(figures, tmp_path)
    assert "cumulative_energy" in paths
    assert all((tmp_path / name).is_file() for name in paths.values())
