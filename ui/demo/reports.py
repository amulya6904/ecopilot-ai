"""Approved project-scoped reports and evidence downloads."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ui.artifact_views import PROJECT_ROOT, is_approved_display_path
from ui.formatting import project_relative

from .components import product_header, safe_page_error
from .data import (
    DEMO_MODE_REPLAY,
    ArtifactLoadError,
    approved_report_files,
    load_approved_file_bytes,
    load_demo_context,
)


GROUPS = {
    "Executive results": {
        "final_summary.json",
        "executive_summary.md",
        "judge_summary.json",
    },
    "Aligned telemetry": {
        "aligned_facility_telemetry.csv",
        "aligned_zone_telemetry.csv",
    },
    "Comparison data": {
        "energy_comparison.csv",
        "demand_comparison.csv",
        "comfort_comparison.csv",
        "cost_comparison.csv",
        "carbon_comparison.csv",
        "action_summary.csv",
    },
    "Validity and safety": {
        "compatibility_report.json",
        "reproducibility_report.json",
        "safety_metrics.json",
        "reliability_metrics.json",
        "comparison_manifest.json",
    },
    "Submission package": {
        "submission_manifest.json",
    },
    "Project documentation": {
        "README.md",
        "SYSTEM_ARCHITECTURE.md",
        "DEMO_SCRIPT.md",
    },
}


def _mime(path: Path) -> str:
    return {
        ".json": "application/json",
        ".csv": "text/csv",
        ".md": "text/markdown",
    }.get(path.suffix.lower(), "application/octet-stream")


def _classification(path: Path) -> str:
    if path.name in {"README.md", "SYSTEM_ARCHITECTURE.md", "DEMO_SCRIPT.md"}:
        return "Repository documentation"
    if path.name in {
        "cost_comparison.csv",
        "carbon_comparison.csv",
    }:
        return "Derived from configured assumption"
    return "Official EnergyPlus comparison"


def _source_phase(path: Path) -> str:
    if "phase11" in path.parts or path.name == "submission_manifest.json":
        return "Phase 11"
    if path.suffix.lower() == ".md" and path.name != "executive_summary.md":
        return "Repository"
    return "Phase 10"


def render_reports(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    product_header(
        streamlit,
        title="Reports",
        subtitle=(
            "Download the official comparison, aligned telemetry, safety, "
            "reproducibility, and submission documentation from approved paths."
        ),
        eyebrow="Evidence library",
        mode=mode,
    )
    try:
        context = load_demo_context()
        files = approved_report_files(context["index"])
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="Report bundle unavailable",
            message=exc.public_message,
            next_step="Build the Phase 10 submission export, then refresh.",
            diagnostics=exc.diagnostics,
        )
        return

    summary = context["summary"]
    streamlit.caption(
        f"Comparison · {summary['comparison_id']} · "
        f"{summary['claim_status']} · verified artifact replay"
    )
    by_name = {path.name: path for path in files}
    for group, names in GROUPS.items():
        streamlit.subheader(group)
        for name in sorted(names):
            path = by_name.get(name)
            with streamlit.container(border=True, key=f"report-{name.lower()}"):
                columns = streamlit.columns([4, 2], vertical_alignment="top")
                with columns[0]:
                    streamlit.markdown(f"**{name}**")
                    streamlit.caption(
                        f"{_source_phase(path or Path(name))} · "
                        f"{_classification(path or Path(name))}"
                    )
                    if path:
                        streamlit.code(
                            project_relative(path, PROJECT_ROOT),
                            language="text",
                        )
                        streamlit.caption(
                            f"{path.stat().st_size / 1024:,.1f} KiB · "
                            f"updated "
                            f"{datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()} · "
                            f"run {summary['comparison_id']}"
                        )
                    else:
                        streamlit.caption("Artifact unavailable")
                with columns[1]:
                    if path and path.is_file() and is_approved_display_path(path):
                        streamlit.download_button(
                            "Download",
                            data=load_approved_file_bytes(path),
                            file_name=path.name,
                            mime=_mime(path),
                            key=f"report-download-{name}",
                            icon=":material/download:",
                        )
                    else:
                        streamlit.button(
                            "Unavailable",
                            disabled=True,
                            key=f"report-missing-{name}",
                        )
    streamlit.caption(
        "Downloads are restricted to the repository README, docs directory, "
        "and approved results directories. Raw external or user-selected paths "
        "are never accepted."
    )


__all__ = ["GROUPS", "render_reports"]
