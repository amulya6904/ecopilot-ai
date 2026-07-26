"""Judge-facing architecture page using only local native components."""

from typing import Any

import pandas as pd

from .components import badge_row


ARCHITECTURE_FLOW = (
    "EnergyPlus",
    "Runtime telemetry",
    "MCP tools",
    "Local qwen3:4b",
    "Structured proposal",
    "Deterministic validation",
    "Phase 9 safety supervisor",
    "Actuator injection",
    "Post-action verification",
    "Rollback / fallback",
    "Quantitative comparison",
)

LAYER_ROWS = (
    (
        "Simulation engine",
        "EnergyPlus 26.1 model, weather, schedules, and annual physics.",
        "Official telemetry and diagnostics",
    ),
    (
        "Cognitive layer",
        "Local qwen3:4b generates a compact typed advisory proposal.",
        "Advisory only",
    ),
    (
        "Communication layer",
        "Local MCP stdio tools expose bounded official evidence.",
        "Read-only by default",
    ),
    (
        "Safety layer",
        "Deterministic rules own validation, intervention, and recovery.",
        "Final control authority",
    ),
    (
        "Runtime-control layer",
        "One discovered cooling-setpoint actuator is written and observed.",
        "Verified injection and reset",
    ),
    (
        "Evidence and comparison layer",
        "Manifest compatibility, alignment, metrics, claim gate, and audit.",
        "Reproducible result",
    ),
)

TECHNOLOGY_ROWS = (
    ("Python", "Typed orchestration, validation, tests, and artifacts"),
    ("EnergyPlus", "Official building simulation and telemetry"),
    (
        "pyenergyplus Runtime/Data Transfer API",
        "Callbacks, handles, actuator write, and observation",
    ),
    ("Ollama", "Local inference service"),
    ("qwen3:4b", "Open-source advisory model"),
    ("MCP", "Bounded local tool and resource protocol"),
    ("Streamlit", "Offline-capable dashboard and downloads"),
    ("pandas + Altair", "Artifact processing and display-only charts"),
)


def render_architecture(streamlit: Any) -> None:
    streamlit.title("Architecture")
    streamlit.caption(
        "EnergyPlus-first, local, typed, safety-supervised, and auditable."
    )
    badge_row(
        streamlit,
        ("Official EnergyPlus", "Advisory only", "Safety supervised"),
    )

    streamlit.subheader("Closed-loop evidence flow")
    streamlit.code(
        "\n  ↓\n".join(ARCHITECTURE_FLOW),
        language="text",
    )
    streamlit.info(
        "The LLM never writes directly to an EnergyPlus actuator. All "
        "proposals are converted into typed candidates and must pass "
        "deterministic validation and safety supervision.",
        icon=":material/shield:",
    )

    streamlit.subheader("System layers")
    streamlit.dataframe(
        pd.DataFrame(
            LAYER_ROWS,
            columns=("Layer", "Responsibility", "Trust boundary"),
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Layer": streamlit.column_config.TextColumn(pinned=True),
        },
    )

    streamlit.subheader("Technology stack")
    streamlit.dataframe(
        pd.DataFrame(
            TECHNOLOGY_ROWS,
            columns=("Technology", "Role"),
        ),
        hide_index=True,
        width="stretch",
    )

    with streamlit.expander(
        "Design scope",
        icon=":material/info:",
    ):
        streamlit.markdown(
            """
- The retained EnergyPlus example model is used consistently in both runs.
- The quantitative policy controls one cooling-setpoint actuator.
- Genuine PMV/PPD is unavailable; occupied temperature is the explicit proxy.
- Local-model latency depends on CPU and memory, so the LLM is never called
  inside an EnergyPlus callback.
- The final quantitative comparison uses the deterministic policy for repeatable
  annual evidence; qwen3:4b remains an optional bounded advisory source.
"""
        )


__all__ = [
    "ARCHITECTURE_FLOW",
    "LAYER_ROWS",
    "TECHNOLOGY_ROWS",
    "render_architecture",
]
