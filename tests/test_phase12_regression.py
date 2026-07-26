import pytest

from ui.demo.data import load_demo_context


def test_phase10_metrics_hashes_and_approved_claim_are_preserved():
    context = load_demo_context()
    summary = context["summary"]
    assert summary["baseline_energy_kwh"] == pytest.approx(
        58568.21190808616,
        abs=1e-8,
    )
    assert summary["controlled_energy_kwh"] == pytest.approx(
        58562.58583227383,
        abs=1e-8,
    )
    assert summary["energy_reduction_kwh"] == pytest.approx(
        5.626075812331692,
        abs=1e-8,
    )
    assert summary["energy_reduction_percent"] == pytest.approx(
        0.009606022839080278,
        abs=1e-10,
    )
    assert summary["baseline_peak_demand_kw"] == pytest.approx(
        21.050576908787157,
        abs=1e-12,
    )
    assert summary["controlled_peak_demand_kw"] == pytest.approx(
        21.050577252463818,
        abs=1e-12,
    )
    assert summary["comfort_metrics"]["comfort_change_percent_points"] == pytest.approx(
        0.16718913270637614,
        abs=1e-12,
    )
    assert summary["cost_metrics"]["absolute_cost_reduction"] == pytest.approx(
        45.008606498653535,
        abs=1e-8,
    )
    assert summary["carbon_metrics"]["absolute_carbon_reduction_kg"] == pytest.approx(
        3.983261675122776,
        abs=1e-8,
    )
    assert summary["severe_count"] == summary["fatal_count"] == 0
    assert summary["alignment"]["matched_intervals"] == 8760
    assert summary["exact_approved_statement"].startswith(
        "Under the documented compatible EnergyPlus experiment"
    )
    assert context["baseline_summary"]["base_model_hash"] == (
        "5467be2c8504b32512b81320bd8500c91cecd566ec3ab9684006c18fc7229a50"
    )
    assert context["controlled_summary"]["weather_hash"] == (
        "b24506e034c43d31950862232b97b404e573de4c8bee04204f62d0890bcae478"
    )

