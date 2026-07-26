import pandas as pd

from comparison.artifacts import (
    REQUIRED_COMPARISON_ARTIFACTS,
    write_comparison_bundle,
)
from comparison.settings import ComparisonSettings
def test_complete_comparison_artifact_bundle(tmp_path):
    empty = pd.DataFrame()
    settings = ComparisonSettings(repository_root=tmp_path)
    baseline = tmp_path / "results" / "official"
    controlled = tmp_path / "results" / "closed_loop" / "phase8" / "run"
    baseline.mkdir(parents=True)
    controlled.mkdir(parents=True)
    directory = write_comparison_bundle(
        comparison_id="comparison",
        baseline_summary={},
        controlled_summary={},
        compatibility_report={},
        final_summary={"comparison_valid": False, "claim_status": "comparison_invalid"},
        judge_summary={},
        reliability_metrics={},
        agent_metrics={},
        safety_metrics={},
        reproducibility_report={},
        executive_summary="# Summary\n",
        energy_comparison=empty,
        demand_comparison=empty,
        comfort_comparison=empty,
        cost_comparison=empty,
        carbon_comparison=empty,
        action_summary=empty,
        aligned_facility=empty,
        aligned_zone=empty,
        baseline_artifact=baseline,
        controlled_artifact=controlled,
        settings=settings,
    )
    assert all((directory / name).is_file() for name in REQUIRED_COMPARISON_ARTIFACTS)
    assert (directory / "comparison_manifest.json").is_file()
