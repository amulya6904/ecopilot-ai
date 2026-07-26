"""Premium architecture narrative using local assets and native components."""

from pathlib import Path
from typing import Any

from .components import (
    methodology_item,
    page_header,
    scope_note,
    section_divider,
    status_badge,
    trust_boundary,
)


ASSETS_ROOT = Path(__file__).parents[1] / "assets"

ARCHITECTURE_FLOW = (
    "EnergyPlus Runtime",
    "Telemetry Exchange",
    "MCP Server",
    "qwen3:4b Agent",
    "Typed Proposal",
    "Deterministic Validator",
    "Safety Supervisor",
    "Actuator Injection",
    "Post-Action Verification",
    "Fallback / Rollback",
)

SAFETY_REASONS = (
    ("01", "LLM output is advisory", "No model response reaches an actuator directly."),
    ("02", "Typed schema validation", "Malformed or incomplete proposals are rejected."),
    ("03", "Maximum 1°C control delta", "Candidate movement is bounded before injection."),
    ("04", "Comfort and demand constraints", "Deterministic thresholds gate every action."),
    ("05", "Stale-data rejection", "Old telemetry cannot authorize a new decision."),
    ("06", "Actuator verification", "Applied and observed setpoints must agree."),
    ("07", "Reset to Phase 5 baseline", "The fixed schedule remains the safe recovery state."),
    ("08", "Emergency autonomy disable", "Critical faults remove autonomous authority."),
)

TECHNOLOGY_ROWS = (
    ("Python 3.12", "Typed orchestration, validation, tests, and artifacts"),
    ("EnergyPlus 26.1", "Official physics, runtime state, and annual telemetry"),
    (
        "pyenergyplus Runtime/Data Transfer API",
        "Callbacks, handle discovery, actuator write, and observation",
    ),
    ("MCP", "Bounded local tools and resources over stdio"),
    ("Ollama", "Local inference service with thinking disabled"),
    ("qwen3:4b", "Compact structured advisory proposal"),
    ("Pydantic", "Typed proposal and evidence boundaries"),
    ("Streamlit + Altair", "Offline presentation and artifact visualization"),
)


def render_architecture(streamlit: Any) -> None:
    page_header(
        streamlit,
        label="System architecture",
        title="A closed loop with deterministic authority",
        subtitle=(
            "The LLM reasons over bounded EnergyPlus evidence, but never "
            "writes directly to an actuator."
        ),
    )
    with streamlit.container(horizontal=True):
        status_badge(streamlit, "Official EnergyPlus", status="info")
        status_badge(streamlit, "Local advisory", status="info")
        status_badge(streamlit, "Deterministic authority", status="verified")

    section_divider(
        streamlit,
        "Control and evidence flow",
        "A local, typed chain separates physical simulation, advisory "
        "reasoning, final authority, and proof.",
    )
    streamlit.image(
        str(ASSETS_ROOT / "architecture_flow.svg"),
        width="stretch",
    )
    streamlit.caption(" → ".join(ARCHITECTURE_FLOW))

    section_divider(
        streamlit,
        "Trust boundaries",
        "Authority narrows as evidence approaches the physical actuator.",
    )
    trust_boundary(
        streamlit,
        title="Evidence boundary",
        description=(
            "MCP exposes bounded official artifacts. qwen3:4b can only return "
            "a typed advisory candidate."
        ),
        authority="Read-only",
    )
    trust_boundary(
        streamlit,
        title="Decision boundary",
        description=(
            "Python schema checks and Phase 9 deterministic rules approve, "
            "clamp, hold, reject, or fall back."
        ),
        authority="Final authority",
    )
    trust_boundary(
        streamlit,
        title="Runtime boundary",
        description=(
            "One discovered EnergyPlus cooling-setpoint actuator is written, "
            "observed, reset, and audited."
        ),
        authority="Verified path",
    )

    section_divider(
        streamlit,
        "Why this architecture is safe",
        "The safety case is structural: bounded input, deterministic authority, "
        "verified effect, and an explicit recovery state.",
    )
    grid = streamlit.container(horizontal=True, gap="large")
    for number, title, description in SAFETY_REASONS:
        with grid.container(
            key=f"editorial-sequence-safety-{number}",
            width=250,
        ):
            streamlit.caption(number)
            streamlit.subheader(title)
            streamlit.write(description)

    section_divider(
        streamlit,
        "Technology specification",
        "All presentation assets and runtime dependencies remain local.",
    )
    columns = streamlit.columns(2, gap="large")
    for index, (technology, role) in enumerate(TECHNOLOGY_ROWS):
        with columns[index % 2]:
            methodology_item(streamlit, label=technology, value=role)

    scope_note(
        streamlit,
        "This is a safety-supervised single-zone proof of concept, not a "
        "production building-control certification. Genuine PMV/PPD is "
        "unavailable in the retained example model.",
    )


__all__ = [
    "ARCHITECTURE_FLOW",
    "SAFETY_REASONS",
    "TECHNOLOGY_ROWS",
    "render_architecture",
]
