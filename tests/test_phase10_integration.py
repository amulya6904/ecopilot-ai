import json
from dataclasses import replace
from pathlib import Path

import pytest

from comparison.artifact_loader import (
    load_baseline_artifact,
    load_controlled_artifact,
)
from comparison.compatibility import compare_run_compatibility
from comparison.runner import run_comparison
from comparison.settings import COMPARISON_SETTINGS


@pytest.mark.energyplus_comparison
def test_real_phase10_comparison_and_dashboard_loader(tmp_path):
    baseline = load_baseline_artifact()
    controlled = load_controlled_artifact()
    assert compare_run_compatibility(
        baseline.identity, controlled.identity
    ).comparable
    settings = replace(
        COMPARISON_SETTINGS,
        comparison_artifact_root=tmp_path / "comparisons",
    )
    result = run_comparison(
        controlled_path=controlled.directory,
        settings=settings,
    )
    assert result.success
    summary = json.loads(
        (result.artifact_directory / "final_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["comfort_gate_passed"]
    assert summary["claim_status"]
    assert summary["severe_count"] == 0
    assert summary["fatal_count"] == 0
    assert (result.artifact_directory / "comparison_manifest.json").is_file()
