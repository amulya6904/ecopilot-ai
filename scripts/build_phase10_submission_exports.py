"""Build a compact Phase 10 submission package without raw EnergyPlus output."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from comparison.artifacts import write_json
from comparison.settings import COMPARISON_SETTINGS


def _latest_comparison() -> Path:
    root = COMPARISON_SETTINGS.resolve(
        COMPARISON_SETTINGS.comparison_artifact_root
    )
    candidates = [
        item
        for item in root.iterdir()
        if item.is_dir() and (item / "final_summary.json").is_file()
    ] if root.is_dir() else []
    if not candidates:
        raise RuntimeError("No Phase 10 result is available for export.")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    comparison = _latest_comparison()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    export = comparison / f"submission_export-{stamp}"
    export.mkdir(parents=True, exist_ok=False)
    selected = [
        "final_summary.json",
        "judge_summary.json",
        "compatibility_report.json",
        "reproducibility_report.json",
        "comparison_manifest.json",
        "energy_comparison.csv",
        "demand_comparison.csv",
        "comfort_comparison.csv",
        "cost_comparison.csv",
        "carbon_comparison.csv",
        "action_summary.csv",
        "executive_summary.md",
    ]
    for name in selected:
        _copy(comparison / name, export / "results" / name)
    charts = comparison / "charts"
    if charts.is_dir():
        for chart in charts.glob("*.html"):
            _copy(chart, export / "charts" / chart.name)
    root = Path(COMPARISON_SETTINGS.repository_root)
    documents = [
        "README.md",
        "PROJECT_SCOPE.md",
        "docs/SYSTEM_ARCHITECTURE.md",
        "docs/OFFICIAL_REQUIREMENTS_MAPPING.md",
        "docs/PHASE10_QUANTITATIVE_COMPARISON.md",
        "docs/FINAL_RESULTS.md",
        "docs/REPRODUCIBILITY.md",
        "docs/LLM_AGENT.md",
        "docs/AGENT_PROMPTING.md",
        "docs/DEMO_SCRIPT.md",
        "docs/PRESENTATION_OUTLINE.md",
        "docs/SUBMISSION_CHECKLIST.md",
    ]
    for relative in documents:
        source = root / relative
        if source.is_file():
            _copy(source, export / "documentation" / relative)
    manifest = _json(comparison / "comparison_manifest.json")
    baseline_dir = Path(manifest["baseline_artifact_directory"])
    controlled_dir = Path(manifest["controlled_artifact_directory"])
    _copy(
        baseline_dir / "phase5_energyplus_baseline_manifest.json",
        export / "manifests" / "baseline_manifest.json",
    )
    _copy(
        controlled_dir / "controlled_manifest.json",
        export / "manifests" / "controlled_run_manifest.json",
    )
    controlled_manifest = _json(
        controlled_dir / "controlled_manifest.json"
    )
    write_json(
        export / "manifests" / "model_manifest.json",
        {
            "base_model_path": controlled_manifest["base_model_path"],
            "base_model_hash": controlled_manifest["base_model_hash"],
            "runtime_model_path": controlled_manifest["runtime_model_path"],
            "runtime_model_hash": controlled_manifest["runtime_model_hash"],
            "weather_path": controlled_manifest["weather_path"],
            "weather_hash": controlled_manifest["weather_hash"],
        },
    )
    audit_root = root / "results" / "audit"
    audit_files = [
        {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
        }
        for path in audit_root.glob("*.jsonl")
        if path.is_file()
    ] if audit_root.is_dir() else []
    write_json(export / "audit_file_index.json", {"files": audit_files})
    produced = [
        str(path.relative_to(export))
        for path in export.rglob("*")
        if path.is_file()
    ]
    write_json(
        export / "submission_export_manifest.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "comparison_directory": str(comparison),
            "files": produced,
            "raw_energyplus_outputs_included": False,
        },
    )
    print(json.dumps({
        "success": True,
        "export_directory": str(export),
        "file_count": len(produced) + 1,
        "raw_energyplus_outputs_included": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
