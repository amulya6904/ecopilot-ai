"""Repeat deterministic Phase 10 execution and persist a tolerance report."""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pandas as pd

from comparison.artifact_loader import load_controlled_artifact
from comparison.artifacts import write_json
from comparison.reproducibility import compare_repeated_results
from comparison.runner import run_comparison, run_controlled_evaluation
from comparison.settings import COMPARISON_SETTINGS


def _latest_comparison() -> Path:
    root = COMPARISON_SETTINGS.resolve(
        COMPARISON_SETTINGS.comparison_artifact_root
    )
    candidates = [
        item
        for item in root.iterdir() if item.is_dir()
        and (item / "final_summary.json").is_file()
        and (item / "comparison_manifest.json").is_file()
    ] if root.is_dir() else []
    if not candidates:
        raise RuntimeError("No Phase 10 comparison exists to reproduce.")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _refresh(directory: Path) -> None:
    manifest_path = directory / "comparison_manifest.json"
    manifest = _json(manifest_path)
    files = manifest.setdefault("files", {})
    for name in (
        "final_summary.json",
        "judge_summary.json",
        "reproducibility_report.json",
    ):
        path = directory / name
        files[name] = {
            "sha256": _digest(path),
            "bytes": path.stat().st_size,
        }
    write_json(manifest_path, manifest)


def _update(
    directory: Path,
    report: dict[str, Any],
) -> None:
    write_json(directory / "reproducibility_report.json", report)
    final = _json(directory / "final_summary.json")
    final["reproducible"] = bool(report["reproducible"])
    write_json(directory / "final_summary.json", final)
    judge = _json(directory / "judge_summary.json")
    judge["reproducible"] = bool(report["reproducible"])
    write_json(directory / "judge_summary.json", judge)
    _refresh(directory)


def main() -> int:
    first_directory = _latest_comparison()
    first = _json(first_directory / "final_summary.json")
    if first.get("comparison_mode") != "reproducible_policy":
        report = {
            "reproducible": False,
            "mode": str(first.get("comparison_mode")),
            "first_comparison_id": str(first.get("comparison_id")),
            "second_comparison_id": None,
            "model_hashes_match": True,
            "weather_hashes_match": True,
            "telemetry_shape_match": True,
            "energy_within_tolerance": False,
            "peak_demand_within_tolerance": False,
            "comfort_within_tolerance": False,
            "action_counts_match": False,
            "comparison_status_match": False,
            "mismatches": ["LLM-assisted mode is not bit-reproducible."],
            "limitations": [
                "Model, prompt version, and action history are preserved instead."
            ],
            "tolerance": COMPARISON_SETTINGS.reproducibility_tolerance,
        }
        _update(first_directory, report)
        print(json.dumps(report, indent=2))
        return 0
    first_manifest = _json(
        first_directory / "comparison_manifest.json"
    )
    first_controlled_path = Path(
        first_manifest["controlled_artifact_directory"]
    )
    first_controlled = load_controlled_artifact(first_controlled_path)
    repeated_controlled = run_controlled_evaluation(
        mode="reproducible_policy"
    )
    if not repeated_controlled.success:
        raise RuntimeError("Repeated controlled evaluation failed.")
    repeated_comparison = run_comparison(
        controlled_path=repeated_controlled.artifact_directory
    )
    second_directory = repeated_comparison.artifact_directory
    second = repeated_comparison.summary
    second_controlled = load_controlled_artifact(
        repeated_controlled.artifact_directory
    )
    first_action_count = len(
        pd.read_csv(first_directory / "action_summary.csv")
    )
    second_action_count = len(
        pd.read_csv(second_directory / "action_summary.csv")
    )
    report_model = compare_repeated_results(
        first,
        second,
        first_identity=first_controlled.identity.model_dump(mode="json"),
        second_identity=second_controlled.identity.model_dump(mode="json"),
        first_action_count=first_action_count,
        second_action_count=second_action_count,
    )
    report = report_model.model_dump(mode="json")
    _update(first_directory, report)
    _update(second_directory, report)
    print(json.dumps(report, indent=2))
    print(f"First comparison: {first_directory}")
    print(f"Repeated comparison: {second_directory}")
    return 0 if report["reproducible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
