"""Deterministic seven-scene, three-minute demo replay."""

from typing import Any

import pandas as pd

from ui.components import status_badge
from ui.formatting import format_energy, format_percent

from .charts import filtered_line_chart
from .components import closed_loop_pipeline, product_header, safe_page_error
from .data import (
    CONTROLLED_ZONE,
    DEMO_MODE_REPLAY,
    ArtifactLoadError,
    load_comparison_csv,
    load_demo_context,
    load_zone_telemetry,
)


SCENES = (
    "Command Center",
    "Telemetry",
    "AI Copilot",
    "Safe Decision",
    "Unsafe Action",
    "Analytics",
    "Closing",
)


def _reset_demo(streamlit: Any) -> None:
    streamlit.session_state["guided_demo_scene"] = 0
    streamlit.session_state["guided-reset-control"] = None


def _scene_command_center(streamlit: Any, context: dict[str, Any]) -> None:
    summary = context["summary"]
    streamlit.subheader("The complete system is verified and ready to replay")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("EnergyPlus", "Verified"),
            ("MCP", "Ready"),
            ("qwen3:4b", "Saved response"),
            ("Safety", "Active"),
            ("Actuator", "Verified"),
            ("Scenarios", "22/22"),
        ):
            streamlit.metric(label, value, border=True)
    streamlit.metric(
        "Verified facility-energy reduction",
        format_energy(summary["energy_reduction_kwh"], compact=True),
        delta=format_percent(summary["energy_reduction_percent"], 4),
        border=True,
    )


def _scene_telemetry(streamlit: Any, context: dict[str, Any]) -> None:
    zones = load_zone_telemetry(index=context["index"])
    controlled = zones.loc[zones["energyplus_zone_name"].eq(CONTROLLED_ZONE)]
    occupied = controlled.loc[
        pd.to_numeric(controlled["occupancy_controlled"], errors="coerce").fillna(0)
        > 0
    ]
    row = (occupied if not occupied.empty else controlled).iloc[-1]
    streamlit.subheader("EnergyPlus telemetry · SPACE1-1")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Timestamp", str(row["timestamp"])),
            ("Temperature", f"{row['indoor_temperature_c_controlled']:.2f} °C"),
            ("Occupancy", f"{row['occupancy_controlled']:.0f} people"),
            ("Cooling setpoint", f"{row['cooling_setpoint_c_controlled']:.1f} °C"),
            ("Source", "EnergyPlus aligned telemetry"),
        ):
            streamlit.metric(label, value, border=True)
    status_badge(streamlit, "Controlled zone", status="verified")


def _scene_copilot(streamlit: Any, context: dict[str, Any]) -> None:
    phase7 = context.get("phase7", {})
    proposal = phase7.get("proposal", {})
    streamlit.subheader("Saved qwen3:4b advisory")
    streamlit.write(proposal.get("reason", "No saved advisory reason is available."))
    streamlit.json(
        {
            "zone": proposal.get("energyplus_zone_name"),
            "current_setpoint_c": proposal.get("current_setpoint_c"),
            "proposed_setpoint_c": proposal.get("proposed_setpoint_c"),
            "confidence": proposal.get("confidence"),
            "advisory_only": proposal.get("advisory_only"),
            "applied_to_energyplus": proposal.get("applied_to_energyplus"),
        },
        expanded=False,
    )
    streamlit.caption(
        "MCP tools · "
        + ", ".join(
            str(item.get("tool"))
            for item in phase7.get("tools", [])
            if item.get("tool")
        )
    )


def _scene_safe_decision(streamlit: Any, context: dict[str, Any]) -> None:
    runtime = context.get("llm_runtime", {}).get("summary", {})
    closed_loop_pipeline(
        streamlit,
        (
            {
                "name": "LLM candidate",
                "output": f"{runtime.get('raw_llm_requested_setpoint_c', '—')} °C",
                "status": "Advisory",
                "status_kind": "warning",
                "source": "Saved Phase 8 LLM-assisted replay",
            },
            {
                "name": "Direction validation",
                "output": runtime.get("fallback_reason", "Not recorded"),
                "status": "Intervened",
                "status_kind": "warning",
                "source": "Deterministic validator",
            },
            {
                "name": "Safe fallback",
                "output": f"{runtime.get('fallback_action_setpoint_c', '—')} °C",
                "status": "Approved",
                "source": "Runtime fallback",
            },
            {
                "name": "Actuator application",
                "output": f"{runtime.get('applied_setpoint_c', '—')} °C",
                "status": "Verified",
                "source": "EnergyPlus Runtime API",
            },
            {
                "name": "Reset",
                "output": f"{runtime.get('setpoint_after_reset_c', '—')} °C",
                "status": "Verified",
                "source": "Phase 5 baseline",
            },
        ),
    )


def _scene_unsafe(streamlit: Any, context: dict[str, Any]) -> None:
    faults = context.get("safety_run", {}).get("faults", [])
    rejected = next(
        (
            item
            for item in faults
            if item.get("scenario") == "Unknown zone"
        ),
        faults[0] if faults else {},
    )
    streamlit.subheader("Unsafe proposal rejected before actuator access")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Proposal", rejected.get("scenario", "Unavailable")),
            ("Decision", rejected.get("actual_outcome", "Unavailable")),
            ("Rule", rejected.get("expected_rule", "Unavailable")),
            ("Fallback", "Baseline / last-known-safe"),
            ("Actuator", "Protected · no unsafe write"),
        ):
            with streamlit.container(border=True):
                streamlit.caption(label.upper())
                streamlit.markdown(f"**{value}**")
    streamlit.page_link(
        "app_pages/safety.py",
        label="Open interactive unsafe-proposal demo",
        icon=":material/shield:",
    )


def _scene_analytics(streamlit: Any, context: dict[str, Any]) -> None:
    energy = load_comparison_csv(
        "energy_comparison.csv",
        index=context["index"],
    ).copy()
    energy["timestamp"] = pd.to_datetime(energy["timestamp"], errors="coerce")
    strongest = pd.to_numeric(
        energy["cumulative_energy_reduction_kwh"],
        errors="coerce",
    ).abs().idxmax()
    center = energy.loc[strongest, "timestamp"]
    display = energy.loc[
        energy["timestamp"].between(
            center - pd.Timedelta(days=21),
            center + pd.Timedelta(days=21),
        )
    ]
    streamlit.subheader("Measured annual outcome")
    filtered_line_chart(
        streamlit,
        display,
        series={
            "baseline_cumulative_energy_kwh": "Fixed-schedule baseline",
            "controlled_cumulative_energy_kwh": "Safety-supervised controlled",
        },
        y_title="Cumulative facility electricity (kWh)",
        source="Phase 10 energy_comparison.csv · selected difference window",
        zero=False,
    )
    streamlit.caption(
        "Demand is essentially unchanged. Comfort proxy improved +0.167 pp. "
        "PMV is unavailable."
    )


def _scene_closing(streamlit: Any, context: dict[str, Any]) -> None:
    summary = context["summary"]
    streamlit.subheader("Evidence before exaggeration")
    streamlit.info(
        str(summary["exact_approved_statement"]),
        icon=":material/verified:",
    )
    with streamlit.container(horizontal=True, gap="small"):
        streamlit.metric(
            "Energy saved",
            format_energy(summary["energy_reduction_kwh"], compact=True),
            border=True,
        )
        streamlit.metric(
            "Comfort change",
            f"{summary['comfort_metrics']['comfort_change_percent_points']:+.3f} pp",
            border=True,
        )
        streamlit.metric("Safety", "22/22", border=True)
        streamlit.metric("Severe / fatal", "0 / 0", border=True)
    streamlit.caption(
        "Conservative single-zone scope · deterministic safety authority · "
        "reproducible official EnergyPlus evidence."
    )


def render_guided_demo(streamlit: Any) -> None:
    streamlit.session_state.setdefault("guided_demo_scene", 0)
    scene_index = int(streamlit.session_state["guided_demo_scene"])
    scene_index = max(0, min(scene_index, len(SCENES) - 1))
    streamlit.session_state["guided_demo_scene"] = scene_index
    product_header(
        streamlit,
        title=f"Scene {scene_index + 1} · {SCENES[scene_index]}",
        subtitle="A deterministic seven-scene walkthrough designed for a three-minute demonstration.",
        eyebrow="Guided demo",
        mode=DEMO_MODE_REPLAY,
    )
    streamlit.progress(
        (scene_index + 1) / len(SCENES),
        text=f"Step {scene_index + 1} of {len(SCENES)}",
    )
    try:
        context = load_demo_context()
        renderers = (
            _scene_command_center,
            _scene_telemetry,
            _scene_copilot,
            _scene_safe_decision,
            _scene_unsafe,
            _scene_analytics,
            _scene_closing,
        )
        renderers[scene_index](streamlit, context)
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="Guided replay unavailable",
            message=exc.public_message,
            next_step="Restore the latest verified Phase 7–10 artifacts.",
            diagnostics=exc.diagnostics,
        )

    controls = streamlit.container(horizontal=True, horizontal_alignment="distribute")
    if controls.button(
        "Back",
        disabled=scene_index == 0,
        icon=":material/arrow_back:",
        key="guided-back",
    ):
        streamlit.session_state["guided_demo_scene"] = scene_index - 1
        streamlit.rerun()
    if controls.button(
        "Exit demo",
        icon=":material/close:",
        key="guided-exit",
    ):
        streamlit.session_state["guided_demo_scene"] = 0
        streamlit.switch_page("app_pages/command_center.py")
    controls.pills(
        "Demo controls",
        ("Reset demo",),
        key="guided-reset-control",
        label_visibility="collapsed",
        on_change=_reset_demo,
        args=(streamlit,),
    )
    if controls.button(
        "Next",
        type="primary",
        disabled=scene_index == len(SCENES) - 1,
        icon=":material/arrow_forward:",
        key="guided-next",
    ):
        streamlit.session_state["guided_demo_scene"] = scene_index + 1
        streamlit.rerun()


__all__ = ["SCENES", "render_guided_demo"]
