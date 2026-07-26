"""Atomic, auditable Phase 10 comparison artifact bundle."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any
import uuid

import pandas as pd

from energyplus.baseline.artifacts import json_safe

from .charts import build_chart_figures, write_charts
from .settings import COMPARISON_SETTINGS, ComparisonSettings


REQUIRED_COMPARISON_ARTIFACTS = (
    "comparison_manifest.json",
    "compatibility_report.json",
    "baseline_summary.json",
    "controlled_summary.json",
    "final_summary.json",
    "judge_summary.json",
    "energy_comparison.csv",
    "demand_comparison.csv",
    "comfort_comparison.csv",
    "cost_comparison.csv",
    "carbon_comparison.csv",
    "reliability_metrics.json",
    "agent_metrics.json",
    "safety_metrics.json",
    "action_summary.csv",
    "aligned_facility_telemetry.csv",
    "aligned_zone_telemetry.csv",
    "reproducibility_report.json",
    "executive_summary.md",
)


def new_comparison_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-phase10-comparison-{uuid.uuid4().hex[:8]}"


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    _atomic_text(
        path,
        json.dumps(json_safe(value), indent=2, allow_nan=False) + "\n",
    )


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    _atomic_text(path, frame.to_csv(index=False))


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_comparison_bundle(
    *,
    comparison_id: str,
    baseline_summary: dict[str, Any],
    controlled_summary: dict[str, Any],
    compatibility_report: dict[str, Any],
    final_summary: dict[str, Any],
    judge_summary: dict[str, Any],
    reliability_metrics: dict[str, Any],
    agent_metrics: dict[str, Any],
    safety_metrics: dict[str, Any],
    reproducibility_report: dict[str, Any],
    executive_summary: str,
    energy_comparison: pd.DataFrame,
    demand_comparison: pd.DataFrame,
    comfort_comparison: pd.DataFrame,
    cost_comparison: pd.DataFrame,
    carbon_comparison: pd.DataFrame,
    action_summary: pd.DataFrame,
    aligned_facility: pd.DataFrame,
    aligned_zone: pd.DataFrame,
    baseline_artifact: Path,
    controlled_artifact: Path,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> Path:
    directory = settings.resolve(settings.comparison_artifact_root) / comparison_id
    directory.mkdir(parents=True, exist_ok=False)
    json_files = {
        "compatibility_report.json": compatibility_report,
        "baseline_summary.json": baseline_summary,
        "controlled_summary.json": controlled_summary,
        "final_summary.json": final_summary,
        "judge_summary.json": judge_summary,
        "reliability_metrics.json": reliability_metrics,
        "agent_metrics.json": agent_metrics,
        "safety_metrics.json": safety_metrics,
        "reproducibility_report.json": reproducibility_report,
    }
    csv_files = {
        "energy_comparison.csv": energy_comparison,
        "demand_comparison.csv": demand_comparison,
        "comfort_comparison.csv": comfort_comparison,
        "cost_comparison.csv": cost_comparison,
        "carbon_comparison.csv": carbon_comparison,
        "action_summary.csv": action_summary,
        "aligned_facility_telemetry.csv": aligned_facility,
        "aligned_zone_telemetry.csv": aligned_zone,
    }
    for name, value in json_files.items():
        write_json(directory / name, value)
    for name, frame in csv_files.items():
        write_csv(directory / name, frame)
    _atomic_text(directory / "executive_summary.md", executive_summary)
    figures = build_chart_figures(
        energy=energy_comparison,
        demand=demand_comparison,
        comfort=comfort_comparison,
        cost=cost_comparison,
        carbon=carbon_comparison,
        actions=action_summary,
        reliability=reliability_metrics,
        safety=safety_metrics,
    )
    chart_files = write_charts(figures, directory / "charts")
    produced = [
        path for path in directory.iterdir() if path.is_file()
    ]
    manifest = {
        "manifest_version": 1,
        "generator_version": "ecopilot-phase10-v1",
        "comparison_id": comparison_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_artifact_directory": str(baseline_artifact.resolve()),
        "controlled_artifact_directory": str(controlled_artifact.resolve()),
        "classification": "official_energyplus_quantitative_comparison",
        "comparison_valid": final_summary["comparison_valid"],
        "claim_status": final_summary["claim_status"],
        "files": {
            path.name: {
                "sha256": _hash(path),
                "bytes": path.stat().st_size,
            }
            for path in produced
        },
        "charts": chart_files,
        "lightweight_results_used": False,
    }
    write_json(directory / "comparison_manifest.json", manifest)
    missing = [
        name
        for name in REQUIRED_COMPARISON_ARTIFACTS
        if not (directory / name).is_file()
    ]
    if missing:
        raise RuntimeError(
            "Phase 10 comparison bundle is incomplete: " + ", ".join(missing)
        )
    return directory


__all__ = [
    "REQUIRED_COMPARISON_ARTIFACTS",
    "new_comparison_id",
    "write_comparison_bundle",
    "write_csv",
    "write_json",
]
