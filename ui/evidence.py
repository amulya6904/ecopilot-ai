"""Project-scoped evidence library rendered as a restrained editorial list."""

from collections import defaultdict
from pathlib import Path
from typing import Any

from .artifact_views import evidence_records, is_approved_display_path
from .components import evidence_row, error_state, page_header, section_divider


GROUP_ORDER = (
    "Official baseline",
    "MCP verification",
    "LLM evidence",
    "Runtime actuator proof",
    "Safety validation",
    "Quantitative comparison",
    "Reproducibility",
    "Submission package",
)

GROUP_METADATA = {
    "Official baseline": (
        "Phase 5",
        "Frozen annual EnergyPlus reference evidence.",
    ),
    "MCP verification": (
        "Phase 6",
        "Bounded local tool access and append-only audit evidence.",
    ),
    "LLM evidence": (
        "Phase 7",
        "Local qwen3:4b advisory records with no actuator authority.",
    ),
    "Runtime actuator proof": (
        "Phase 8",
        "Discovered handle, applied action, observation, and reset proof.",
    ),
    "Safety validation": (
        "Phase 9",
        "Deterministic decisions, fault injection, and recovery evidence.",
    ),
    "Quantitative comparison": (
        "Phase 10",
        "Compatible, aligned, claim-gated annual comparison evidence.",
    ),
    "Reproducibility": (
        "Phase 10",
        "Independent repeatability report and matching hashes.",
    ),
    "Submission package": (
        "Phase 11",
        "Documentation, index, manifest, and compact deliverables.",
    ),
}


def render_evidence(streamlit: Any) -> None:
    page_header(
        streamlit,
        label="Evidence library",
        title="Verified artifacts, ready to inspect",
        subtitle=(
            "Every displayed path is project-relative and constrained to "
            "approved evidence roots. Downloads never expose files outside "
            "the repository evidence boundary."
        ),
    )
    records = evidence_records()
    if not records:
        error_state(
            streamlit,
            title="No evidence catalogue available",
            explanation="No approved Phase 5–11 artifacts were discovered.",
            affected_feature="Evidence list and downloads",
            next_step="Run the documented validation scripts and refresh.",
        )
        return

    grouped: dict[str, list[object]] = defaultdict(list)
    for record in records:
        grouped[record.group].append(record)

    for group_name in GROUP_ORDER:
        group_records = sorted(grouped.get(group_name, []), key=lambda item: item.name)
        if not group_records:
            continue
        phase, description = GROUP_METADATA[group_name]
        section_divider(streamlit, group_name, description)
        for item in group_records:
            path = Path(item.path)
            downloadable = (
                path.is_file()
                and is_approved_display_path(path)
                and path.stat().st_size <= 25_000_000
            )
            evidence_row(
                streamlit,
                title=item.name,
                phase=phase,
                classification=item.classification,
                run_id=item.run_id,
                verified=path.exists() and item.success is not False,
                description=description,
                relative_path=item.display_path,
                download_path=path if downloadable else None,
                download_key=f"evidence-download-{group_name}-{path.name}",
            )


__all__ = [
    "GROUP_METADATA",
    "GROUP_ORDER",
    "render_evidence",
]
