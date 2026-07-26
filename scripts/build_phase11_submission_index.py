"""Build the compact Phase 11 submission index without copying raw evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parents[1].resolve()
OUTPUT_ROOT = PROJECT_ROOT / "results" / "submission" / "phase11"
COMPARISON_ROOT = PROJECT_ROOT / "results" / "comparison" / "phase10"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _latest_directory(
    root: Path,
    required_filename: str,
    *,
    require_reproducible: bool = False,
) -> Path | None:
    if not root.is_dir():
        return None
    candidates = sorted(
        (
            item
            for item in root.iterdir()
            if item.is_dir() and (item / required_filename).is_file()
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not require_reproducible:
        return candidates[0] if candidates else None
    for directory in candidates:
        try:
            summary = _read_json(directory / required_filename)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if summary.get("comparison_valid") and summary.get("reproducible"):
            return directory
    return None


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _item(
    path: Path,
    *,
    purpose: str,
    phase: str,
    classification: str,
    required: bool,
    upload_format: str,
) -> dict[str, Any]:
    exists = path.is_file()
    return {
        "file": _relative(path),
        "purpose": purpose,
        "source_phase": phase,
        "classification": classification,
        "required": required,
        "recommended_upload_format": upload_format,
        "exists": exists,
        "bytes": path.stat().st_size if exists else None,
        "sha256": _sha256(path) if exists else None,
    }


def build_submission_index() -> tuple[Path, Path]:
    comparison = _latest_directory(
        COMPARISON_ROOT,
        "final_summary.json",
        require_reproducible=True,
    )
    if comparison is None:
        raise FileNotFoundError(
            "A valid reproducible Phase 10 comparison is required."
        )
    summary = _read_json(comparison / "final_summary.json")
    safety = _latest_directory(
        PROJECT_ROOT / "results" / "safety" / "phase9",
        "run_metadata.json",
    )
    agent = _latest_directory(
        PROJECT_ROOT / "results" / "agent" / "phase7",
        "run_metadata.json",
    )
    export_candidates = sorted(
        comparison.glob("submission_export-*"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    compact_export = (
        export_candidates[0] / "submission_export_manifest.json"
        if (
            export_candidates
            and export_candidates[0].is_dir()
            and (
                export_candidates[0] / "submission_export_manifest.json"
            ).is_file()
        )
        else comparison / "executive_summary.md"
    )

    definitions = [
        (
            PROJECT_ROOT / "README.md",
            "Project overview, setup, measured result, scope, and evidence guide",
            "Phase 11",
            "submission_document",
            True,
            "Markdown / repository landing page",
        ),
        (
            PROJECT_ROOT / "requirements.txt",
            "Pinned project dependency entry point",
            "Phase 1–11",
            "source_dependency_manifest",
            True,
            "Text",
        ),
        (
            PROJECT_ROOT / "app.py",
            "Offline Streamlit dashboard entry point",
            "Phase 11",
            "source_code",
            True,
            "Repository source",
        ),
        (
            PROJECT_ROOT
            / "energyplus"
            / "models"
            / "baseline"
            / "phase5_baseline.idf",
            "Official fixed-schedule EnergyPlus baseline model",
            "Phase 5",
            "official_energyplus_baseline_model",
            True,
            "IDF",
        ),
        (
            PROJECT_ROOT
            / "energyplus"
            / "models"
            / "modified"
            / "phase4_telemetry_model.idf",
            "Derived telemetry/runtime EnergyPlus model",
            "Phase 4–8",
            "energyplus_runtime_model",
            True,
            "IDF",
        ),
        (
            PROJECT_ROOT
            / "results"
            / "official"
            / "phase5_energyplus_baseline_manifest.json",
            "Frozen baseline model, weather, source, and output evidence",
            "Phase 5",
            "official_energyplus_baseline_manifest",
            True,
            "JSON",
        ),
        (
            PROJECT_ROOT / "docs" / "SYSTEM_ARCHITECTURE.md",
            "Required architecture report and trust boundaries",
            "Phase 11",
            "submission_document",
            True,
            "Markdown and optional PDF",
        ),
        (
            PROJECT_ROOT / "docs" / "LLM_AGENT.md",
            "Local model, prompt, tool, timeout, and fallback design",
            "Phase 7 / 11",
            "submission_document",
            True,
            "Markdown and optional PDF",
        ),
        (
            PROJECT_ROOT / "docs" / "FINAL_RESULTS.md",
            "Exact result interpretation and contextual assumptions",
            "Phase 10 / 11",
            "submission_document",
            True,
            "Markdown and optional PDF",
        ),
        (
            PROJECT_ROOT / "docs" / "DEMO_SCRIPT.md",
            "Three-minute judge demo script and backup flow",
            "Phase 11",
            "submission_document",
            True,
            "Markdown",
        ),
        (
            PROJECT_ROOT / "docs" / "PRESENTATION_OUTLINE.md",
            "Fourteen-slide presentation content",
            "Phase 11",
            "submission_document",
            True,
            "Markdown; convert to PPTX/PDF manually",
        ),
        (
            PROJECT_ROOT / "docs" / "SUBMISSION_CHECKLIST.md",
            "Final human and automated packaging checks",
            "Phase 11",
            "submission_document",
            True,
            "Markdown",
        ),
        (
            comparison / "final_summary.json",
            "Exact official comparison result and claim gate",
            "Phase 10",
            "official_energyplus_quantitative_comparison",
            True,
            "JSON",
        ),
        (
            comparison / "comparison_manifest.json",
            "Comparison file hashes and provenance",
            "Phase 10",
            "official_energyplus_comparison_manifest",
            True,
            "JSON",
        ),
        (
            comparison / "reproducibility_report.json",
            "Repeatability relationship for the displayed comparison",
            "Phase 10",
            "deterministic_reproducibility",
            True,
            "JSON",
        ),
        (
            compact_export,
            "Compact judge-facing comparison export; raw annual telemetry omitted",
            "Phase 10",
            "submission_export",
            True,
            "ZIP when available; otherwise Markdown",
        ),
    ]
    if safety:
        definitions.append(
            (
                safety / "run_metadata.json",
                "Latest Phase 9 safety-validation run metadata",
                "Phase 9",
                "safety_supervised_energyplus_runtime_validation",
                True,
                "JSON",
            )
        )
    if agent:
        definitions.append(
            (
                agent / "run_metadata.json",
                "Latest local qwen3:4b advisory run evidence",
                "Phase 7",
                "llm_advisory_proposal",
                True,
                "JSON",
            )
        )

    items = [
        _item(
            path,
            purpose=purpose,
            phase=phase,
            classification=classification,
            required=required,
            upload_format=upload_format,
        )
        for (
            path,
            purpose,
            phase,
            classification,
            required,
            upload_format,
        ) in definitions
    ]
    manifest = {
        "manifest_version": 1,
        "classification": "phase11_submission_reference_manifest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "comparison_id": summary["comparison_id"],
        "scope": (
            "References compact source and evidence files without duplicating "
            "large raw EnergyPlus telemetry."
        ),
        "preserved_result": {
            "baseline_energy_kwh": summary["baseline_energy_kwh"],
            "controlled_energy_kwh": summary["controlled_energy_kwh"],
            "energy_reduction_kwh": summary["energy_reduction_kwh"],
            "energy_reduction_percent": summary["energy_reduction_percent"],
            "comfort_change_percentage_points": summary["comfort_metrics"][
                "comfort_change_percent_points"
            ],
            "peak_demand_interpretation": "essentially_unchanged",
            "severe_count": summary["severe_count"],
            "fatal_count": summary["fatal_count"],
        },
        "items": items,
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_ROOT / "submission_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    index_path = OUTPUT_ROOT / "SUBMISSION_INDEX.md"
    rows = [
        "# Phase 11 submission index",
        "",
        (
            "This index references existing source and verified evidence. It "
            "does not duplicate large annual telemetry."
        ),
        "",
        f"Displayed Phase 10 comparison: `{summary['comparison_id']}`",
        "",
        "| File | Purpose | Source phase | Classification | Required | Recommended upload format |",
        "|---|---|---|---|:---:|---|",
    ]
    for item in items:
        row = {
            **item,
            "required": "Yes" if item["required"] else "No",
        }
        rows.append(
            "| `{file}` | {purpose} | {source_phase} | {classification} | "
            "{required} | {recommended_upload_format} |".format(
                **row,
            )
        )
    rows.extend(
        [
            "",
            "## Packaging note",
            "",
            (
                "Upload only the files required by the portal. Keep official "
                "artifacts unchanged; if machine-local provenance must be "
                "redacted for publication, create a clearly labeled copy."
            ),
            "",
            (
                "Human-only deliverables still required: public repository URL, "
                "three-minute video, final presentation export, screenshots, "
                "license decision, and portal upload verification."
            ),
            "",
        ]
    )
    index_path.write_text("\n".join(rows), encoding="utf-8")
    return index_path, manifest_path


def main() -> int:
    index_path, manifest_path = build_submission_index()
    print(_relative(index_path))
    print(_relative(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
