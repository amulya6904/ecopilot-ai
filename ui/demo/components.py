"""Reusable native Streamlit components for the Phase 12 product pages."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ui.artifact_views import PROJECT_ROOT
from ui.components import status_badge
from ui.formatting import project_relative

from .data import DEMO_MODE_REPLAY


def product_header(
    streamlit: Any,
    *,
    title: str,
    subtitle: str,
    eyebrow: str,
    mode: str | None = None,
) -> None:
    with streamlit.container(key="product-header"):
        streamlit.caption(eyebrow.upper())
        streamlit.title(title)
        streamlit.write(subtitle)
        if mode:
            status_badge(
                streamlit,
                "Verified Artifact Replay"
                if mode == DEMO_MODE_REPLAY
                else "Live Services",
                status="verified" if mode == DEMO_MODE_REPLAY else "info",
            )


def system_status_strip(
    streamlit: Any,
    items: Iterable[tuple[str, str, str]],
) -> None:
    with streamlit.container(
        key="system-status-strip",
        horizontal=True,
        gap="small",
    ):
        for label, value, note in items:
            with streamlit.container(border=True, key=f"status-{label.lower()}"):
                streamlit.caption(label.upper())
                streamlit.markdown(f"**{value}**")
                streamlit.caption(note)


def kpi_card(
    streamlit: Any,
    *,
    label: str,
    value: str,
    note: str,
    badge: str | None = None,
    delta: str | None = None,
) -> None:
    with streamlit.container(border=True, key=f"kpi-{label.lower().replace(' ', '-')}"):
        streamlit.metric(label, value, delta=delta)
        if badge:
            status_badge(streamlit, badge, status="verified")
        streamlit.caption(note)


def closed_loop_pipeline(
    streamlit: Any,
    stages: Iterable[dict[str, str]],
) -> None:
    with streamlit.container(
        key="closed-loop-pipeline",
        horizontal=True,
        gap="small",
    ):
        for number, stage in enumerate(stages, start=1):
            with streamlit.container(
                border=True,
                key=f"pipeline-stage-{number}",
            ):
                streamlit.caption(f"{number:02d} · {stage['name']}".upper())
                streamlit.markdown(f"**{stage['output']}**")
                status_badge(
                    streamlit,
                    stage["status"],
                    status=stage.get("status_kind", "verified"),
                )
                streamlit.caption(stage["source"])
                if stage.get("timestamp"):
                    streamlit.caption(f"Timestamp · {stage['timestamp']}")
                if stage.get("duration"):
                    streamlit.caption(stage["duration"])


def decision_spotlight(
    streamlit: Any,
    context: dict[str, Any],
) -> None:
    phase7 = context.get("phase7", {})
    metadata = phase7.get("metadata", {})
    proposal = phase7.get("proposal", {})
    validation = phase7.get("validation", {})
    tools = phase7.get("tools", [])
    runtime = context.get("llm_runtime", {}).get("summary", {})
    comparison_runtime = context.get("runtime", {}).get("summary", {})
    evidence = {
        str(item.get("metric")): item.get("value")
        for item in proposal.get("evidence", [])
    }
    with streamlit.container(border=True, key="latest-decision"):
        top = streamlit.columns([3, 2], vertical_alignment="top")
        with top[0]:
            streamlit.caption("LATEST AI DECISION · VERIFIED REPLAY")
            streamlit.subheader(
                f"{proposal.get('display_zone_name', 'Open Office')} · "
                f"{proposal.get('energyplus_zone_name', 'SPACE1-1')}"
            )
            streamlit.write(
                proposal.get(
                    "reason",
                    "No verified Phase 7 advisory reason is available.",
                )
            )
        with top[1]:
            status_badge(streamlit, "Advisory only", status="warning")
            status_badge(
                streamlit,
                "Schema valid"
                if validation.get("valid")
                else "Validation unavailable",
                status="verified" if validation.get("valid") else "warning",
            )
            streamlit.caption(
                f"{metadata.get('agent_run_id', 'No run ID')} · "
                f"{metadata.get('model', 'qwen3:4b')}"
            )

        with streamlit.container(horizontal=True, gap="small"):
            for label, value in (
                ("Current setpoint", proposal.get("current_setpoint_c")),
                ("Proposed", proposal.get("proposed_setpoint_c")),
                ("Confidence", proposal.get("confidence")),
                (
                    "Safety status",
                    "Review required"
                    if proposal.get("requires_safety_review")
                    else "Validated",
                ),
                ("Actuator result", "Not applied · advisory only"),
            ):
                with streamlit.container(border=True):
                    streamlit.caption(label.upper())
                    if isinstance(value, (int, float)) and label != "Confidence":
                        streamlit.markdown(f"**{value:.1f} °C**")
                    elif label == "Confidence" and isinstance(value, (int, float)):
                        streamlit.markdown(f"**{value:.0%}**")
                    else:
                        streamlit.markdown(f"**{value if value is not None else 'Unavailable'}**")

        detail = streamlit.columns(3)
        detail[0].caption("OBSERVATION CONTEXT")
        detail[0].write(
            {
                "Timestamp / run": metadata.get(
                    "agent_run_id",
                    "Unavailable",
                ),
                "Selected zone": proposal.get(
                    "energyplus_zone_name",
                    "Unavailable",
                ),
                "Occupancy": (
                    "Eligible occupied zone"
                    if evidence.get("eligible_occupied_non_plenum_zone")
                    else "Not retained in proposal"
                ),
                "Outdoor condition": "Not retained in Phase 7 proposal",
                "Demand evidence": (
                    f"{evidence['peak_facility_demand_kw']:.6f} kW baseline peak"
                    if isinstance(
                        evidence.get("peak_facility_demand_kw"),
                        (int, float),
                    )
                    else "Unavailable"
                ),
            }
        )
        detail[1].caption("EXPLICIT AGENT OUTPUT")
        detail[1].write(
            {
                "Decision type": proposal.get("decision_type", "Unavailable"),
                "Objective": proposal.get("objective", "Unavailable"),
                "Expected energy effect": proposal.get(
                    "expected_effect",
                    {},
                ).get("energy", "Unavailable"),
                "Fallback used": bool(metadata.get("fallback_used", False)),
                "MCP tools": len(tools),
            }
        )
        detail[2].caption("SEPARATE PHASE 10 CONTROL RESULT")
        detail[2].write(
            {
                "Baseline": comparison_runtime.get("baseline_setpoint_c"),
                "Requested": comparison_runtime.get("requested_setpoint_c"),
                "Approved": comparison_runtime.get("approved_setpoint_c"),
                "Applied": comparison_runtime.get("applied_setpoint_c"),
                "Actuator writes": comparison_runtime.get(
                    "actuator_write_count"
                ),
                "Safety authority": "Deterministic",
            }
        )
        if tools:
            with streamlit.expander(
                "MCP tool calls and durations",
                icon=":material/hub:",
            ):
                streamlit.dataframe(
                    [
                        {
                            "Tool": item.get("tool"),
                            "Status": (
                                "Success"
                                if item.get("success")
                                else "Failed"
                            ),
                            "Duration (ms)": item.get("duration_ms"),
                        }
                        for item in tools
                    ],
                    hide_index=True,
                )

        if runtime:
            streamlit.info(
                "Separate verified LLM-assisted runtime replay: the raw LLM "
                f"requested {runtime.get('raw_llm_requested_setpoint_c', '—')} °C; "
                "deterministic direction validation rejected that candidate and "
                f"applied a {runtime.get('fallback_action_setpoint_c', '—')} °C "
                "fallback before resetting to baseline.",
                icon=":material/shield:",
            )


def artifact_source(
    streamlit: Any,
    path: Path,
    *,
    label: str = "Source",
) -> None:
    streamlit.caption(f"{label} · {project_relative(path, PROJECT_ROOT)}")


def safe_page_error(
    streamlit: Any,
    *,
    title: str,
    message: str,
    next_step: str,
    diagnostics: str | None = None,
) -> None:
    streamlit.error(f"**{title}** — {message}", icon=":material/error:")
    streamlit.write(f"**Safe recovery:** {next_step}")
    if diagnostics:
        with streamlit.expander(
            "Technical diagnostics",
            icon=":material/troubleshoot:",
        ):
            streamlit.code(diagnostics, language="text")


__all__ = [
    "artifact_source",
    "closed_loop_pipeline",
    "decision_spotlight",
    "kpi_card",
    "product_header",
    "safe_page_error",
    "system_status_strip",
]
