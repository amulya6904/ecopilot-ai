"""Ten-step guided demonstration backed only by persisted evidence."""

from dataclasses import dataclass
from typing import Any

from .components import (
    page_header,
    secondary_button,
    section_divider,
    status_badge,
)


@dataclass(frozen=True)
class DemoStep:
    number: str
    title: str
    happens: str
    artifact: str
    evidence: str
    metric: str
    page: str
    status: str = "Verified"


DEMO_STEPS = (
    DemoStep(
        "01",
        "Load official baseline",
        "Open the frozen fixed-schedule annual EnergyPlus reference.",
        "results/official/phase5_energyplus_baseline_manifest.json",
        "The manifest fixes the model, weather, schedules, and reporting basis.",
        "58,568.211908 kWh",
        "app_pages/phase5.py",
    ),
    DemoStep(
        "02",
        "Inspect EnergyPlus telemetry",
        "Review aligned facility and zone measurements from the official run.",
        "results/official/phase5_energyplus_baseline_summary.json",
        "Facility and zone records remain separated and unit-labelled.",
        "8,760 facility intervals",
        "app_pages/phase5.py",
    ),
    DemoStep(
        "03",
        "Show MCP tool evidence",
        "Inspect bounded local access to official EnergyPlus artifacts.",
        "results/audit/mcp_tool_calls.jsonl",
        "The local stdio layer is read-only by default and append-only audited.",
        "16 tools · 6 resources",
        "app_pages/phase6.py",
    ),
    DemoStep(
        "04",
        "Show qwen3:4b advisory proposal",
        "Open a compact typed proposal generated from bounded evidence.",
        "results/agent/phase7/",
        "The local model proposes; it never receives actuator authority.",
        "Advisory only",
        "app_pages/phase7.py",
    ),
    DemoStep(
        "05",
        "Show rejected unsafe direction",
        "Demonstrate deterministic rejection of a proposal outside safe intent.",
        "results/safety/phase9/",
        "Schema, comfort, demand, freshness, and direction checks run in Python.",
        "Decision · Reject",
        "app_pages/phase9.py",
    ),
    DemoStep(
        "06",
        "Show validated fallback",
        "Trace an invalid or unsafe candidate back to the fixed baseline state.",
        "results/safety/phase9/",
        "Fallback is explicit, classified, persisted, and independently tested.",
        "Fallback · Verified",
        "app_pages/phase9.py",
    ),
    DemoStep(
        "07",
        "Show real setpoint injection",
        "Inspect the one approved cooling-setpoint write in the EnergyPlus Runtime API.",
        "results/closed_loop/phase8/",
        "The discovered handle, requested value, and applied value are retained.",
        "1 verified actuator path",
        "app_pages/phase8.py",
    ),
    DemoStep(
        "08",
        "Show post-action verification",
        "Compare the approved, applied, and observed setpoint on a later callback.",
        "results/closed_loop/phase8/",
        "A mismatch cannot silently continue; reset and rollback remain available.",
        "Observed change · Verified",
        "app_pages/phase8.py",
    ),
    DemoStep(
        "09",
        "Show safety fault-injection result",
        "Review every decision outcome and recovery path under injected faults.",
        "results/safety/phase9/",
        "Approve, clamp, hold, reject, fallback, and emergency fallback are exercised.",
        "22 / 22 passed",
        "app_pages/phase9.py",
    ),
    DemoStep(
        "10",
        "Show final official comparison",
        "Open the compatible, aligned, reproducible annual EnergyPlus result.",
        "results/comparison/phase10/",
        "The claim gate preserves the small result, comfort context, and unchanged peak.",
        "5.626076 kWh",
        "app_pages/phase10.py",
    ),
)


def render_demo_flow(streamlit: Any) -> None:
    page_header(
        streamlit,
        label="Three-minute guided demonstration",
        title="A complete proof, without the wait",
        subtitle=(
            "Ten pre-generated evidence stops tell the full story. No EnergyPlus "
            "run or local-model request starts automatically."
        ),
    )
    section_divider(
        streamlit,
        "Presentation sequence",
        "Move from the official reference to advisory reasoning, deterministic "
        "authority, physical control, safety proof, and measured impact.",
    )
    for step in DEMO_STEPS:
        with streamlit.container(key=f"demo-step-{step.number}"):
            columns = streamlit.columns(
                [1, 5, 2],
                gap="large",
                vertical_alignment="top",
            )
            columns[0].caption(step.number)
            with columns[1]:
                streamlit.subheader(step.title)
                streamlit.write(step.happens)
                streamlit.markdown(f"**Why it matters:** {step.evidence}")
                streamlit.caption(f"Artifact · {step.artifact}")
            with columns[2]:
                status_badge(streamlit, step.status, status="verified")
                streamlit.metric("Key evidence", step.metric)
                secondary_button(
                    streamlit,
                    "Open detailed page",
                    page=step.page,
                    key=f"demo-{step.number}",
                )

    with streamlit.expander(
        "Presenter notes",
        expanded=False,
        icon=":material/movie:",
    ):
        streamlit.markdown(
            """
1. Begin on Home and state the trust boundary before discussing the result.
2. Use Architecture to show that qwen3:4b is advisory only.
3. Spend the middle minute on rejection, fallback, real injection, and 22/22 safety.
4. End on Quantitative Results. Say **5.626 kWh / 0.0096%**, describe peak
   demand as essentially unchanged, and disclose the single-zone scope.
5. If local inference is cold or slow, stay on persisted artifacts. Never wait
   for an annual EnergyPlus run during the three-minute recording.
"""
        )


__all__ = ["DEMO_STEPS", "DemoStep", "render_demo_flow"]
