"""Presentation-ready, artifact-backed opening page for EcoPilot AI."""

from pathlib import Path
from typing import Any

from .artifact_views import latest_phase10_directory, load_phase10_bundle
from .components import (
    compact_metric,
    editorial_callout,
    empty_state,
    eyebrow,
    primary_button,
    secondary_button,
    section_divider,
    status_badge,
)
from .constants import PROJECT_SUBTITLE, PROJECT_TITLE
from .formatting import format_energy, format_percent, peak_change_label


ASSETS_ROOT = Path(__file__).parents[1] / "assets"

HERO_PARAGRAPH = (
    "EcoPilot AI connects a high-fidelity EnergyPlus digital twin to a local "
    "open-source LLM through MCP tools, validates every proposal through "
    "deterministic safety rules, and injects verified setpoint actions back "
    "into the live simulation."
)

CORE_BLOCKS = (
    ("01", "EnergyPlus digital twin", "Official annual physics and telemetry."),
    ("02", "Runtime telemetry", "Typed facility, zone, demand, and actuator state."),
    ("03", "MCP tool layer", "Bounded local evidence over audited stdio."),
    ("04", "Local LLM advisory", "qwen3:4b emits a compact typed proposal."),
    ("05", "Safety supervisor", "Deterministic rules retain final authority."),
    ("06", "Actuator injection", "One verified cooling-setpoint write path."),
    ("07", "Verification and fallback", "Observe, reset, rollback, and recover."),
    ("08", "Quantitative evidence", "Aligned, claim-gated, reproducible artifacts."),
)

SYSTEM_STATUS = (
    ("EnergyPlus", "Verified", "verified"),
    ("MCP", "16 tools / 6 resources", "verified"),
    ("qwen3:4b", "Local", "info"),
    ("Runtime actuator", "Verified", "verified"),
    ("Safety tests", "22/22", "verified"),
    ("Severe / Fatal", "0 / 0", "verified"),
)


def _render_status_panel(streamlit: Any) -> None:
    with streamlit.container(key="status-panel"):
        eyebrow(streamlit, "System status")
        for label, value, status in SYSTEM_STATUS:
            columns = streamlit.columns([3, 2], vertical_alignment="center")
            columns[0].caption(label)
            with columns[1]:
                status_badge(streamlit, value, status=status)


def _render_result_strip(streamlit: Any, summary: dict[str, object]) -> None:
    comfort_change = summary["comfort_metrics"]["comfort_change_percent_points"]
    demand = summary["demand_metrics"]
    peak_label = peak_change_label(
        demand["absolute_peak_reduction_kw"],
        tolerance_kw=1e-6,
    ).replace("Essentially ", "")
    with streamlit.container(
        key="result-strip",
        horizontal=True,
        horizontal_alignment="distribute",
        gap="medium",
    ):
        compact_metric(
            streamlit,
            label="Verified facility-energy reduction",
            value=format_energy(summary["energy_reduction_kwh"], compact=True),
        )
        compact_metric(
            streamlit,
            label="Reproducible annual reduction",
            value=format_percent(summary["energy_reduction_percent"], 4),
        )
        compact_metric(
            streamlit,
            label="Comfort-proxy change",
            value=f"{float(comfort_change):+.3f} pp",
        )
        compact_metric(
            streamlit,
            label="Peak demand",
            value=peak_label,
        )


def _render_sequence(streamlit: Any) -> None:
    section_divider(
        streamlit,
        "A bounded path from physics to evidence",
        "The local model advises. Typed validation and the deterministic "
        "supervisor decide. Every applied action is observed and recoverable.",
    )
    streamlit.image(
        str(ASSETS_ROOT / "closed_loop_flow.svg"),
        width="stretch",
    )
    grid = streamlit.container(horizontal=True, gap="large")
    for number, title, description in CORE_BLOCKS:
        with grid.container(
            key=f"editorial-sequence-{number}",
            width=250,
        ):
            streamlit.caption(number)
            streamlit.subheader(title)
            streamlit.write(description)


def render_home(streamlit: Any) -> None:
    """Render the opening demo frame without starting any expensive work."""
    hero_left, hero_right = streamlit.columns(
        [5, 2],
        gap="large",
        vertical_alignment="bottom",
    )
    with hero_left:
        with streamlit.container(key="home-hero"):
            eyebrow(streamlit, "Physical AI for building operations")
            streamlit.title(PROJECT_TITLE)
            streamlit.subheader(PROJECT_SUBTITLE)
            streamlit.write(HERO_PARAGRAPH)
            with streamlit.container(horizontal=True, gap="small"):
                primary_button(
                    streamlit,
                    "View Quantitative Results",
                    page="app_pages/phase10.py",
                )
                secondary_button(
                    streamlit,
                    "Explore Closed-Loop Demo",
                    page="app_pages/demo_flow.py",
                )
    with hero_right:
        _render_status_panel(streamlit)

    directory = latest_phase10_directory(require_reproducible=True)
    if directory is None:
        empty_state(
            streamlit,
            "Verified Phase 10 evidence is unavailable. Run the documented "
            "comparison and reproducibility commands, then refresh.",
        )
    else:
        summary = load_phase10_bundle(str(directory.resolve()))["summary"]
        _render_result_strip(streamlit, summary)
        editorial_callout(
            streamlit,
            "Conservative single-zone, safety-first proof of concept.",
        )
        streamlit.caption(f"Source comparison · {summary['comparison_id']}")

    _render_sequence(streamlit)


__all__ = [
    "CORE_BLOCKS",
    "HERO_PARAGRAPH",
    "SYSTEM_STATUS",
    "render_home",
]
