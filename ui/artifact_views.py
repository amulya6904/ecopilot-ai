"""Project-scoped artifact discovery, display paths, and cached readers."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .formatting import project_relative


PROJECT_ROOT = Path(__file__).parents[1].resolve()
RESULTS_ROOT = (PROJECT_ROOT / "results").resolve()
DOCS_ROOT = (PROJECT_ROOT / "docs").resolve()
PHASE10_ROOT = RESULTS_ROOT / "comparison" / "phase10"


@dataclass(frozen=True)
class EvidenceRecord:
    group: str
    name: str
    classification: str
    run_id: str
    timestamp: str
    success: bool | None
    source: str
    path: Path
    required: bool = True

    @property
    def display_path(self) -> str:
        return project_relative(self.path, PROJECT_ROOT)


def is_approved_display_path(path: Path) -> bool:
    resolved = Path(path).resolve()
    approved = (RESULTS_ROOT, DOCS_ROOT)
    if resolved == PROJECT_ROOT / "README.md":
        return True
    return any(
        resolved == root or root in resolved.parents
        for root in approved
    )


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return value


def latest_phase10_directory(*, require_reproducible: bool = True) -> Path | None:
    if not PHASE10_ROOT.is_dir():
        return None
    candidates = sorted(
        (
            item
            for item in PHASE10_ROOT.iterdir()
            if item.is_dir()
            and (item / "comparison_manifest.json").is_file()
            and (item / "final_summary.json").is_file()
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for directory in candidates:
        try:
            summary = _json(directory / "final_summary.json")
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not summary.get("comparison_valid"):
            continue
        if require_reproducible and not summary.get("reproducible"):
            continue
        return directory
    return None


@st.cache_data(max_entries=8, show_spinner=False)
def _load_phase10_bundle_cached(
    directory_text: str,
    fingerprint: tuple[tuple[str, int, int], ...],
) -> dict[str, Any]:
    del fingerprint
    directory = Path(directory_text)

    def read_json(name: str) -> dict[str, Any]:
        return _json(directory / name)

    def read_csv(name: str) -> pd.DataFrame:
        return pd.read_csv(directory / name)

    return {
        "summary": read_json("final_summary.json"),
        "compatibility": read_json("compatibility_report.json"),
        "reliability": read_json("reliability_metrics.json"),
        "agent": read_json("agent_metrics.json"),
        "safety": read_json("safety_metrics.json"),
        "reproducibility": read_json("reproducibility_report.json"),
        "manifest": read_json("comparison_manifest.json"),
        "baseline": read_json("baseline_summary.json"),
        "controlled": read_json("controlled_summary.json"),
        "energy": read_csv("energy_comparison.csv"),
        "demand": read_csv("demand_comparison.csv"),
        "comfort": read_csv("comfort_comparison.csv"),
        "cost": read_csv("cost_comparison.csv"),
        "carbon": read_csv("carbon_comparison.csv"),
        "actions": read_csv("action_summary.csv"),
        "executive": (directory / "executive_summary.md").read_text(
            encoding="utf-8"
        ),
    }


def load_phase10_bundle(directory_text: str) -> dict[str, Any]:
    """Load immutable artifacts with safe path, size, and mtime invalidation."""
    directory = Path(directory_text)
    names = (
        "final_summary.json",
        "compatibility_report.json",
        "reliability_metrics.json",
        "agent_metrics.json",
        "safety_metrics.json",
        "reproducibility_report.json",
        "comparison_manifest.json",
        "baseline_summary.json",
        "controlled_summary.json",
        "energy_comparison.csv",
        "demand_comparison.csv",
        "comfort_comparison.csv",
        "cost_comparison.csv",
        "carbon_comparison.csv",
        "action_summary.csv",
        "executive_summary.md",
    )
    fingerprint = tuple(
        (name, (directory / name).stat().st_mtime_ns, (directory / name).stat().st_size)
        for name in names
    )
    return _load_phase10_bundle_cached(directory_text, fingerprint)


@st.cache_data(max_entries=8, show_spinner=False)
def _load_event_timeline_cached(
    runtime_directory_text: str,
    fingerprint: tuple[tuple[str, int, int], ...],
) -> pd.DataFrame:
    del fingerprint
    runtime_directory = Path(runtime_directory_text)
    rows: list[dict[str, Any]] = []
    for filename, event_type in (
        ("fallback_events.json", "Fallback"),
        ("controlled_rollback_events.json", "Rollback"),
        ("controlled_emergency_events.json", "Emergency"),
    ):
        path = runtime_directory / filename
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                rows.append(
                    {
                        "timestamp": value.get(
                            "simulation_timestamp",
                            value.get("timestamp"),
                        ),
                        "event_type": event_type,
                        "reason": value.get(
                            "reason_code",
                            value.get("reason", "Not recorded"),
                        ),
                        "fallback_value_c": value.get("fallback_value_c"),
                    }
                )
    return pd.DataFrame(
        rows,
        columns=("timestamp", "event_type", "reason", "fallback_value_c"),
    )


def load_phase10_event_timeline(directory_text: str) -> pd.DataFrame:
    """Load project-scoped fallback, rollback, and emergency event evidence."""
    directory = Path(directory_text)
    controlled = _json(directory / "controlled_summary.json")
    runtime_directory = Path(str(controlled["runtime_artifact_directory"])).resolve()
    if not (
        runtime_directory == RESULTS_ROOT
        or RESULTS_ROOT in runtime_directory.parents
    ):
        raise ValueError("Runtime evidence is outside the approved results root.")
    names = (
        "fallback_events.json",
        "controlled_rollback_events.json",
        "controlled_emergency_events.json",
    )
    fingerprint = tuple(
        (
            name,
            (runtime_directory / name).stat().st_mtime_ns,
            (runtime_directory / name).stat().st_size,
        )
        for name in names
    )
    return _load_event_timeline_cached(str(runtime_directory), fingerprint)


def _record_from_json(
    group: str,
    name: str,
    path: Path,
    *,
    classification: str,
    source: str,
    required: bool = True,
) -> EvidenceRecord | None:
    if not path.is_file() or not is_approved_display_path(path):
        return None
    try:
        value = _json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        value = {}
    return EvidenceRecord(
        group=group,
        name=name,
        classification=str(
            value.get("classification", classification)
        ),
        run_id=str(
            value.get(
                "run_id",
                value.get("agent_run_id", value.get("comparison_id", "—")),
            )
        ),
        timestamp=str(
            value.get(
                "created_at",
                value.get("generation_timestamp", "See artifact"),
            )
        ),
        success=(
            bool(value["success"])
            if "success" in value
            else None
        ),
        source=str(value.get("source", source)),
        path=path,
        required=required,
    )


def evidence_records() -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    baseline = _record_from_json(
        "Official baseline",
        "Phase 5 baseline manifest",
        RESULTS_ROOT / "official" / "phase5_energyplus_baseline_manifest.json",
        classification="official_energyplus_baseline",
        source="EnergyPlus",
    )
    if baseline:
        records.append(baseline)

    for group, name, path, classification, source, required in (
        (
            "MCP verification",
            "MCP audit log",
            RESULTS_ROOT / "audit" / "mcp_tool_calls.jsonl",
            "local_mcp_audit",
            "MCP",
            True,
        ),
        (
            "LLM evidence",
            "Agent audit log",
            RESULTS_ROOT / "audit" / "agent_runs.jsonl",
            "advisory_agent_audit",
            "qwen3:4b via Ollama",
            True,
        ),
        (
            "Submission package",
            "System architecture",
            DOCS_ROOT / "SYSTEM_ARCHITECTURE.md",
            "submission_document",
            "Repository",
            True,
        ),
        (
            "Submission package",
            "Demo script",
            DOCS_ROOT / "DEMO_SCRIPT.md",
            "submission_document",
            "Repository",
            True,
        ),
        (
            "Submission package",
            "Submission checklist",
            DOCS_ROOT / "SUBMISSION_CHECKLIST.md",
            "submission_document",
            "Repository",
            True,
        ),
        (
            "Submission package",
            "Presentation outline",
            DOCS_ROOT / "PRESENTATION_OUTLINE.md",
            "submission_document",
            "Repository",
            True,
        ),
        (
            "Submission package",
            "Phase 11 submission manifest",
            RESULTS_ROOT
            / "submission"
            / "phase11"
            / "submission_manifest.json",
            "submission_manifest",
            "Repository",
            True,
        ),
    ):
        if path.is_file() and is_approved_display_path(path):
            records.append(
                EvidenceRecord(
                    group,
                    name,
                    classification,
                    "—",
                    "See artifact",
                    None,
                    source,
                    path,
                    required,
                )
            )

    phase7_root = RESULTS_ROOT / "agent" / "phase7"
    if phase7_root.is_dir():
        latest = max(
            (
                item
                for item in phase7_root.iterdir()
                if item.is_dir() and (item / "run_metadata.json").is_file()
            ),
            key=lambda item: item.stat().st_mtime,
            default=None,
        )
        if latest:
            record = _record_from_json(
                "LLM evidence",
                "Latest advisory summary",
                latest / "run_metadata.json",
                classification="llm_advisory_proposal",
                source="qwen3:4b via Ollama",
            )
            if record:
                records.append(record)

    runtime_root = RESULTS_ROOT / "closed_loop" / "phase8"
    if runtime_root.is_dir():
        latest = max(
            (
                item
                for item in runtime_root.iterdir()
                if item.is_dir()
                and (item / "controlled_summary.json").is_file()
                and (item / "actuator_inventory.json").is_file()
            ),
            key=lambda item: item.stat().st_mtime,
            default=None,
        )
        if latest:
            record = _record_from_json(
                "Runtime actuator proof",
                "Latest controlled-run metadata",
                latest / "controlled_summary.json",
                classification="energyplus_runtime_actuator_control",
                source="pyenergyplus Runtime/Data Transfer API",
            )
            if record:
                records.append(record)

    safety_root = RESULTS_ROOT / "safety" / "phase9"
    if safety_root.is_dir():
        latest = max(
            (
                item
                for item in safety_root.iterdir()
                if item.is_dir() and (item / "run_metadata.json").is_file()
            ),
            key=lambda item: item.stat().st_mtime,
            default=None,
        )
        if latest:
            record = _record_from_json(
                "Safety validation",
                "Latest safety run metadata",
                latest / "run_metadata.json",
                classification="safety_supervised_energyplus_runtime_validation",
                source="EnergyPlus + deterministic supervisor",
            )
            if record:
                records.append(record)

    comparison = latest_phase10_directory(require_reproducible=True)
    if comparison:
        for group, name, filename, classification in (
            (
                "Quantitative comparison",
                "Final comparison summary",
                "final_summary.json",
                "official_energyplus_comparison",
            ),
            (
                "Reproducibility",
                "Reproducibility report",
                "reproducibility_report.json",
                "deterministic_reproducibility",
            ),
            (
                "Quantitative comparison",
                "Comparison manifest",
                "comparison_manifest.json",
                "official_energyplus_comparison_manifest",
            ),
        ):
            record = _record_from_json(
                group,
                name,
                comparison / filename,
                classification=classification,
                source="EnergyPlus",
            )
            if record:
                records.append(record)
        exports = sorted(
            comparison.glob("submission_export-*"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if exports:
            records.append(
                EvidenceRecord(
                    "Submission package",
                    "Latest compact Phase 10 export",
                    "submission_export",
                    comparison.name,
                    "See directory",
                    True,
                    "Repository",
                    exports[0],
                )
            )
    return records


__all__ = [
    "DOCS_ROOT",
    "EvidenceRecord",
    "PHASE10_ROOT",
    "PROJECT_ROOT",
    "RESULTS_ROOT",
    "evidence_records",
    "is_approved_display_path",
    "latest_phase10_directory",
    "load_phase10_bundle",
    "load_phase10_event_timeline",
]
