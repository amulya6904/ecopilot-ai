import json
from pathlib import Path

import pandas as pd

from energyplus.baseline.artifacts import (
    ARTIFACT_FILENAMES,
    write_baseline_artifacts,
)


def _summary() -> dict:
    return {
        "classification": "official_energyplus_baseline",
        "official_result": True,
        "baseline_result": True,
        "ai_controlled": False,
        "closed_loop": False,
        "optimized": False,
        "savings_result": False,
        "success": True,
    }


def test_successful_official_artifacts_are_stable_and_serializable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "results/official"
    frame = pd.DataFrame({"timestamp": [pd.Timestamp("2000-01-01")], "value": [1]})
    manifest = {"base_model_hash": "abc", "weather_hash": "def"}
    paths = write_baseline_artifacts(
        success=True,
        results_root=root,
        zone_telemetry=frame,
        facility_telemetry=frame,
        zone_summary=frame,
        summary=_summary(),
        errors={"records": []},
        metadata={"path": tmp_path, "missing": float("nan")},
        manifest=manifest,
    )
    assert set(paths) == {
        "zone_telemetry", "facility_telemetry", "zone_summary",
        "summary", "errors", "metadata", "manifest",
    }
    assert all(path.is_file() for path in paths.values())
    assert paths["summary"].name == ARTIFACT_FILENAMES["summary"]
    assert json.loads(paths["manifest"].read_text())["base_model_hash"] == "abc"
    assert json.loads(paths["metadata"].read_text())["missing"] is None


def test_failed_run_writes_no_official_summary_and_keeps_raw_output(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "energyplus/output/official/baseline/run/eplusout.err"
    raw.parent.mkdir(parents=True)
    raw.write_text("retained", encoding="utf-8")
    paths = write_baseline_artifacts(
        success=False,
        results_root=tmp_path / "results/official",
        zone_telemetry=pd.DataFrame(),
        facility_telemetry=pd.DataFrame(),
        zone_summary=pd.DataFrame(),
        summary={},
        errors={},
        metadata={},
        manifest={},
    )
    assert paths == {}
    assert not (tmp_path / "results/official").exists()
    assert raw.read_text(encoding="utf-8") == "retained"
    assert not (tmp_path / "results/development").exists()
