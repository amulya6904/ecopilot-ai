import json
from pathlib import Path

import pytest

from ui.artifact_views import latest_phase10_directory, load_phase10_bundle
from ui.phase10 import build_action_impact_table


def test_phase10_exact_metrics_hashes_and_reproducibility_are_preserved():
    directory = latest_phase10_directory(require_reproducible=True)
    assert directory is not None
    bundle = load_phase10_bundle(str(directory.resolve()))
    summary = bundle["summary"]
    assert summary["baseline_energy_kwh"] == pytest.approx(58568.21190808615)
    assert summary["controlled_energy_kwh"] == pytest.approx(58562.58583227383)
    assert summary["energy_reduction_kwh"] == pytest.approx(5.626075812324416)
    assert summary["energy_reduction_percent"] == pytest.approx(
        0.009606022839067856
    )
    assert summary["comfort_metrics"]["comfort_change_percent_points"] == pytest.approx(
        0.16718913270637614
    )
    assert summary["comparison_valid"] is True
    assert summary["claim_status"] == "validated_positive_savings"
    assert summary["severe_count"] == 0
    assert summary["fatal_count"] == 0
    assert summary["comfort_metrics"]["controlled"]["pmv_available"] is False
    assert summary["comfort_metrics"]["controlled"]["comfort_method"] == (
        "occupied_temperature_proxy"
    )
    report = bundle["reproducibility"]
    assert report["reproducible"] is True
    assert report["second_comparison_id"] == summary["comparison_id"]
    assert report["model_hashes_match"] is True
    assert report["weather_hashes_match"] is True
    assert bundle["baseline"]["base_model_hash"] == bundle["controlled"][
        "base_model_hash"
    ]
    assert bundle["baseline"]["weather_hash"] == bundle["controlled"][
        "weather_hash"
    ]


def test_action_impact_table_uses_supported_aligned_fields():
    directory = latest_phase10_directory(require_reproducible=True)
    assert directory is not None
    bundle = load_phase10_bundle(str(directory.resolve()))
    table = build_action_impact_table(
        bundle["actions"],
        bundle["energy"],
        bundle["comfort"],
    )
    assert not table.empty
    assert table["zone"].eq("SPACE1-1").all()
    assert table["baseline_interval_energy_kwh"].notna().all()
    assert table["controlled_interval_energy_kwh"].notna().all()
    assert table["baseline_setpoint_c"].notna().all()


def test_phase9_faults_and_actuator_identifier_are_preserved():
    safety_root = Path("results/safety/phase9")
    validation = max(
        (
            item
            for item in safety_root.glob("*-phase9-validation-*")
            if (item / "fault_injection_results.json").is_file()
        ),
        key=lambda item: item.stat().st_mtime,
    )
    faults = json.loads(
        (validation / "fault_injection_results.json").read_text(encoding="utf-8")
    )
    summary = json.loads((validation / "summary.json").read_text(encoding="utf-8"))
    assert len(faults) == 22
    assert all(item["passed"] for item in faults)
    assert summary["severe_count"] == 0
    assert summary["fatal_count"] == 0

    controlled_root = Path("results/closed_loop/phase8")
    controlled = max(
        (
            item
            for item in controlled_root.iterdir()
            if item.is_dir() and (item / "actuator_inventory.json").is_file()
        ),
        key=lambda item: item.stat().st_mtime,
    )
    inventory = json.loads(
        (controlled / "actuator_inventory.json").read_text(encoding="utf-8")
    )
    identifiers = {
        item["identifier"]
        for item in inventory["actuators"]
        if item.get("identifier")
    }
    assert (
        "Zone Temperature Control|Cooling Setpoint|SPACE1-1" in identifiers
    )
