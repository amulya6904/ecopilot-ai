"""Compact submission-readiness checklist backed by repository state."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_views import PROJECT_ROOT, latest_phase10_directory
from .components import (
    artifact_download,
    page_header,
    section_divider,
    status_badge,
)


@dataclass(frozen=True)
class ChecklistItem:
    label: str
    complete: bool
    note: str


def _exists(relative_path: str) -> bool:
    return (PROJECT_ROOT / relative_path).exists()


def build_checklist() -> dict[str, tuple[ChecklistItem, ...]]:
    """Build the judge-facing checklist from safe local existence checks."""
    latest = latest_phase10_directory(require_reproducible=True)
    screenshots = list((PROJECT_ROOT / "assets" / "screenshots").glob("*.png"))
    return {
        "Repository": (
            ChecklistItem("Source code", _exists("app.py"), "Application and Phase 1–10 modules"),
            ChecklistItem("Requirements", _exists("requirements.txt"), "Pinned Python dependency list"),
            ChecklistItem("README", _exists("README.md"), "Project, result, and quick start"),
            ChecklistItem("Installation guide", _exists("README.md"), "Offline setup documented in README"),
        ),
        "Models": (
            ChecklistItem(
                "Baseline IDF",
                _exists("energyplus/models/baseline/phase5_baseline.idf"),
                "Frozen fixed-schedule model",
            ),
            ChecklistItem(
                "Runtime-control IDF",
                _exists("energyplus/models/modified/phase4_telemetry_model.idf"),
                "Derived actuator-enabled model",
            ),
            ChecklistItem(
                "Weather manifest",
                _exists("results/official/phase5_energyplus_baseline_manifest.json"),
                "Frozen weather hash in official manifest",
            ),
        ),
        "Evidence": (
            ChecklistItem(
                "Baseline artifacts",
                _exists("results/official/phase5_energyplus_baseline_summary.json"),
                "Annual reference summary and telemetry",
            ),
            ChecklistItem(
                "Actuator proof",
                _exists("results/closed_loop/phase8"),
                "Handle, action, observation, and reset",
            ),
            ChecklistItem(
                "Safety validation",
                _exists("results/safety/phase9"),
                "22/22 fault scenarios",
            ),
            ChecklistItem(
                "Comparison report",
                latest is not None,
                "Valid aligned Phase 10 evidence",
            ),
            ChecklistItem(
                "Reproducibility report",
                bool(latest and (latest / "reproducibility_report.json").is_file()),
                "Matching model/weather hashes and repeated metrics",
            ),
        ),
        "Deliverables": (
            ChecklistItem(
                "Architecture report",
                _exists("docs/SYSTEM_ARCHITECTURE.md"),
                "Trust boundary and control architecture",
            ),
            ChecklistItem(
                "Dashboard screenshots",
                bool(screenshots),
                "Capture final desktop and narrow layouts",
            ),
            ChecklistItem(
                "Presentation",
                False,
                "Export the final deck from the documented outline",
            ),
            ChecklistItem(
                "Three-minute video",
                False,
                "Record and upload after final visual QA",
            ),
            ChecklistItem(
                "GitHub URL",
                False,
                "Add the public repository URL in the portal",
            ),
            ChecklistItem(
                "Final ZIP / PDF",
                False,
                "Build only after the portal requirements are confirmed",
            ),
        ),
    }


def render_submission_checklist(streamlit: Any) -> None:
    page_header(
        streamlit,
        label="Submission readiness",
        title="One final quality gate",
        subtitle=(
            "Repository evidence is verified automatically. Human upload, "
            "recording, and portal tasks remain visibly open."
        ),
    )
    checklist = build_checklist()
    complete = sum(item.complete for items in checklist.values() for item in items)
    total = sum(len(items) for items in checklist.values())
    streamlit.metric("Repository-ready checks", f"{complete} / {total}")

    for section, items in checklist.items():
        section_divider(streamlit, section)
        for index, item in enumerate(items):
            with streamlit.container(key=f"check-row-{section}-{index}"):
                columns = streamlit.columns([1, 4, 4], vertical_alignment="center")
                with columns[0]:
                    status_badge(
                        streamlit,
                        "Complete" if item.complete else "Required",
                        status="complete" if item.complete else "warning",
                    )
                columns[1].markdown(f"**{item.label}**")
                columns[2].caption(item.note)

    source = PROJECT_ROOT / "docs" / "SUBMISSION_CHECKLIST.md"
    if source.is_file():
        section_divider(streamlit, "Detailed packaging checklist")
        artifact_download(
            streamlit,
            label="Download detailed checklist",
            path=source,
            key="download-submission-checklist",
        )


__all__ = [
    "ChecklistItem",
    "build_checklist",
    "render_submission_checklist",
]
