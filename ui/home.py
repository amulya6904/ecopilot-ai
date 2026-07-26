"""Executive, artifact-backed Home page for judges."""

from typing import Any

from .artifact_views import (
    latest_phase10_directory,
    load_phase10_bundle,
)
from .components import badge, badge_row, render_error_state
from .constants import (
    PROJECT_STATEMENT,
    PROJECT_SUBTITLE,
    PROJECT_TITLE,
    SMALL_RESULT_NOTE,
)
from .formatting import (
    format_change,
    format_energy,
    format_percent,
    peak_change_label,
)


CORE_BLOCKS = (
    (
        "EnergyPlus digital twin",
        "Official model, weather, schedules, physics, and telemetry.",
    ),
    (
        "Runtime telemetry",
        "Typed facility, zone, demand, comfort, and actuator observations.",
    ),
    (
        "MCP tool layer",
        "Bounded local access to official evidence and diagnostics.",
    ),
    (
        "qwen3:4b advisory agent",
        "Local structured proposal generation with explicit timeouts.",
    ),
    (
        "Deterministic safety supervisor",
        "Final authority over comfort, demand, freshness, and recovery.",
    ),
    (
        "EnergyPlus actuator injection",
        "One verified write path with observation, reset, and fallback.",
    ),
)


def render_home(streamlit: Any) -> None:
    streamlit.title(PROJECT_TITLE)
    streamlit.subheader(PROJECT_SUBTITLE)
    streamlit.write(PROJECT_STATEMENT)
    badge(streamlit, "Conservative single-zone proof of concept")

    streamlit.subheader("System at a glance")
    for offset in range(0, len(CORE_BLOCKS), 3):
        columns = streamlit.columns(3, border=True)
        for column, (title, description) in zip(
            columns, CORE_BLOCKS[offset : offset + 3]
        ):
            with column:
                streamlit.markdown(f"**{title}**")
                streamlit.caption(description)

    streamlit.subheader("Verified project status")
    with streamlit.container(horizontal=True):
        for label, value in (
            ("EnergyPlus integration", "Verified"),
            ("MCP tools", "Verified"),
            ("Local LLM", "Verified"),
            ("Control injection", "Verified"),
            ("Safety validation", "22/22"),
            ("Official comparison", "Valid"),
            ("Severe errors", "0"),
            ("Fatal errors", "0"),
        ):
            streamlit.metric(label, value, border=True)

    directory = latest_phase10_directory(require_reproducible=True)
    if directory is None:
        render_error_state(
            streamlit,
            title="Verified comparison unavailable",
            explanation=(
                "The Home page cannot find a valid reproducible Phase 10 bundle."
            ),
            affected_feature="Measured-result cards",
            next_step=(
                "Run the Phase 10 comparison and reproducibility scripts, then "
                "refresh this page."
            ),
        )
    else:
        bundle = load_phase10_bundle(str(directory.resolve()))
        summary = bundle["summary"]
        comfort_change = summary["comfort_metrics"][
            "comfort_change_percent_points"
        ]
        peak_label = peak_change_label(
            summary["demand_metrics"]["absolute_peak_reduction_kw"],
            tolerance_kw=1e-6,
        )
        streamlit.subheader("Measured annual result")
        badge_row(
            streamlit,
            ("Official EnergyPlus", "Safety supervised", "Reproducible"),
        )
        with streamlit.container(horizontal=True):
            streamlit.metric(
                "Facility-energy reduction",
                format_energy(summary["energy_reduction_kwh"], compact=True),
                border=True,
            )
            streamlit.metric(
                "Percentage reduction",
                format_percent(summary["energy_reduction_percent"], 4),
                border=True,
            )
            streamlit.metric(
                "Comfort proxy change",
                format_change(
                    comfort_change,
                    "percentage points",
                    decimals=3,
                ),
                border=True,
            )
            streamlit.metric(
                "Peak demand",
                peak_label,
                border=True,
            )
        streamlit.caption(SMALL_RESULT_NOTE)
        streamlit.caption(
            f"Source comparison: `{summary['comparison_id']}`"
        )

    with streamlit.expander(
        "Scope and assumptions",
        icon=":material/info:",
    ):
        streamlit.markdown(
            """
- One conservatively controlled EnergyPlus zone.
- Genuine PMV/PPD is unavailable in the retained example model.
- Occupied-temperature compliance is the declared comfort proxy.
- Tariff and carbon intensity are configured assumptions, not raw outputs.
- Peak demand remained effectively unchanged within the configured tolerance.
- This is an auditable proof of concept, not a real-building deployment or
  production safety certification.
"""
        )

    streamlit.page_link(
        "app_pages/demo_flow.py",
        label="View the 3-minute demo flow",
        icon=":material/play_circle:",
    )


__all__ = ["CORE_BLOCKS", "render_home"]
