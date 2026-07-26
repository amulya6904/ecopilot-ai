"""Guided, pre-generated nine-step demonstration for judges."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DemoStep:
    title: str
    happens: str
    artifact: str
    evidence: str
    page: str
    status: str = "Verified"


DEMO_STEPS = (
    DemoStep(
        "Step 1 — Official EnergyPlus baseline",
        "A fixed thermostat schedule runs for the complete annual horizon.",
        "results/official/phase5_energyplus_baseline_manifest.json",
        "58,568.211908 kWh from 8,760 facility intervals.",
        "app_pages/phase5.py",
    ),
    DemoStep(
        "Step 2 — MCP discovery and telemetry",
        "Sixteen bounded local tools expose official evidence over stdio.",
        "results/audit/mcp_tool_calls.jsonl",
        "Read-only tools retain classifications and bounded audit records.",
        "app_pages/phase6.py",
    ),
    DemoStep(
        "Step 3 — Local LLM advisory",
        "qwen3:4b receives bounded evidence and returns a typed proposal.",
        "results/agent/phase7/",
        "The advisory has no direct actuator authority.",
        "app_pages/phase7.py",
    ),
    DemoStep(
        "Step 4 — Deterministic validation",
        "Schema, evidence, bounds, deadband, and runtime checks are applied.",
        "results/agent/phase7/",
        "Invalid output is rejected or replaced by an explicit fallback.",
        "app_pages/phase7.py",
    ),
    DemoStep(
        "Step 5 — Safety supervision",
        "Phase 9 applies comfort, demand, freshness, rate, and oscillation rules.",
        "results/safety/phase9/",
        "22/22 fault scenarios and all six decision outcomes passed.",
        "app_pages/phase9.py",
    ),
    DemoStep(
        "Step 6 — EnergyPlus actuator injection",
        "Only an approved candidate reaches the one discovered write path.",
        "results/closed_loop/phase8/",
        "Control injection and actuator observation are verified.",
        "app_pages/phase8.py",
    ),
    DemoStep(
        "Step 7 — Post-action verification",
        "The next callback checks the observed setpoint and safety response.",
        "results/safety/phase9/",
        "Applied and observed values are linked by action identifiers.",
        "app_pages/phase9.py",
    ),
    DemoStep(
        "Step 8 — Fallback or rollback",
        "Unsafe, stale, oscillating, or mismatched actions restore baseline control.",
        "results/safety/phase9/",
        "Fallback, rollback, and emergency recovery paths are tested.",
        "app_pages/phase9.py",
    ),
    DemoStep(
        "Step 9 — Official quantitative comparison",
        "Compatible annual telemetry is aligned, measured, and claim-gated.",
        "results/comparison/phase10/",
        "5.626076 kWh reduction; comfort proxy improved; peak unchanged.",
        "app_pages/phase10.py",
    ),
)


def render_demo_flow(streamlit: Any) -> None:
    streamlit.title("Three-minute demo flow")
    streamlit.caption(
        "A guided story over pre-generated evidence. No simulation or model "
        "inference starts automatically."
    )
    streamlit.info(
        "Judge Mode is recommended for the recording. Open technical details "
        "only when a judge asks for the underlying evidence.",
        icon=":material/movie:",
    )
    for step in DEMO_STEPS:
        with streamlit.container(border=True):
            with streamlit.container(horizontal=True):
                streamlit.subheader(step.title)
                streamlit.badge(step.status, color="green")
            streamlit.write(step.happens)
            streamlit.caption(f"Source artifact: `{step.artifact}`")
            streamlit.markdown(f"**Evidence:** {step.evidence}")
            streamlit.page_link(
                step.page,
                label="Open this evidence page",
                icon=":material/arrow_forward:",
            )


__all__ = ["DEMO_STEPS", "DemoStep", "render_demo_flow"]
