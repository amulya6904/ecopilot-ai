"""Decision lifecycle page spanning telemetry, LLM, validation, and actuator evidence."""

from typing import Any

import pandas as pd

from ui.components import status_badge

from .charts import decision_timeline_chart
from .components import closed_loop_pipeline, decision_spotlight, product_header, safe_page_error
from .data import (
    CONTROLLED_ZONE,
    DEMO_MODE_REPLAY,
    ArtifactLoadError,
    load_comparison_csv,
    load_demo_context,
)


FILTER_OPTIONS = (
    "approved",
    "rejected",
    "corrected",
    "fallback",
    "rollback",
    "timeout",
    "schema failure",
    "actuator failure",
)


def _category(value: str) -> str:
    return {
        "approve": "approved",
        "approve_with_clamp": "corrected",
        "reject": "rejected",
        "hold": "rejected",
        "emergency_fallback": "fallback",
    }.get(value, value)


def render_decisions(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    product_header(
        streamlit,
        title="Decisions",
        subtitle=(
            "A traceable lifecycle from observed EnergyPlus evidence through "
            "advisory reasoning, deterministic authority, and verified application."
        ),
        eyebrow="Control audit",
        mode=mode,
    )
    streamlit.caption(
        "Only explicit reasons, tool calls, typed proposals, validation results, "
        "and applied outcomes are shown. Hidden chain-of-thought is never stored "
        "or displayed."
    )
    try:
        context = load_demo_context()
        actions = load_comparison_csv(
            "action_summary.csv",
            index=context["index"],
        ).copy()
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="Decision evidence unavailable",
            message=exc.public_message,
            next_step="Restore the Phase 7–10 result artifacts, then refresh.",
            diagnostics=exc.diagnostics,
        )
        return

    decision_spotlight(streamlit, context)
    phase7 = context.get("phase7", {})
    metadata = phase7.get("metadata", {})
    proposal = phase7.get("proposal", {})
    runtime = context.get("llm_runtime", {}).get("summary", {})
    closed_loop_pipeline(
        streamlit,
        (
            {
                "name": "Telemetry observation",
                "output": f"{proposal.get('current_setpoint_c', '—')} °C baseline",
                "status": "Observed",
                "source": "Phase 7 bounded evidence",
            },
            {
                "name": "MCP tools invoked",
                "output": f"{len(phase7.get('tools', []))} read-only calls",
                "status": "Success",
                "source": "tool_calls.json",
                "duration": f"{metadata.get('total_mcp_execution_ms', 0):.0f} ms",
            },
            {
                "name": "LLM proposal",
                "output": f"{proposal.get('proposed_setpoint_c', '—')} °C",
                "status": "Advisory",
                "status_kind": "warning",
                "source": "qwen3:4b",
            },
            {
                "name": "Deterministic validation",
                "output": "Typed schema + direction checks",
                "status": "Valid",
                "source": "Phase 7 / Phase 9",
            },
            {
                "name": "Safety decision",
                "output": (
                    str(runtime.get("fallback_reason") or "Deterministic authority")
                ),
                "status": "Protected",
                "source": "Successful LLM-assisted Phase 8 replay",
            },
            {
                "name": "Actuator application",
                "output": f"{runtime.get('applied_setpoint_c', '—')} °C fallback",
                "status": "Verified",
                "source": "Runtime API · SPACE1-1",
            },
            {
                "name": "Final outcome",
                "output": f"Reset to {runtime.get('setpoint_after_reset_c', '—')} °C",
                "status": "Verified",
                "source": "Post-action evidence",
            },
        ),
    )

    selected_filters = streamlit.pills(
        "Decision filters",
        FILTER_OPTIONS,
        default=("approved", "corrected", "fallback"),
        selection_mode="multi",
        key="decision-filters",
    )
    actions["category"] = actions["decision"].astype(str).map(_category)
    if selected_filters:
        display = actions.loc[actions["category"].isin(selected_filters)].copy()
    else:
        display = actions.copy()
    display["zone"] = CONTROLLED_ZONE

    streamlit.subheader("Applied-action timeline")
    decision_timeline_chart(
        streamlit,
        display,
        source="Phase 10 action_summary.csv",
    )
    streamlit.dataframe(
        display[
            [
                "timestamp",
                "zone",
                "requested_setpoint_c",
                "approved_setpoint_c",
                "applied_setpoint_c",
                "observed_setpoint_c",
                "decision",
                "safety_level",
                "fallback",
                "rollback",
            ]
        ],
        hide_index=True,
    )

    if not display.empty:
        identifiers = display["action_id"].astype(str).tolist()
        selected_id = streamlit.selectbox(
            "Decision record",
            identifiers,
            key="decision-record",
        )
        record = display.loc[display["action_id"].astype(str).eq(selected_id)].iloc[0]
        with streamlit.expander(
            "Expanded decision record",
            expanded=True,
            icon=":material/data_object:",
        ):
            columns = streamlit.columns(3)
            columns[0].metric("Requested", f"{record['requested_setpoint_c']:.1f} °C")
            columns[1].metric("Approved", f"{record['approved_setpoint_c']:.1f} °C")
            columns[2].metric("Applied", f"{record['applied_setpoint_c']:.1f} °C")
            status_badge(
                streamlit,
                str(record["decision"]),
                status="verified" if record["decision"] == "approve" else "warning",
            )
            streamlit.json(
                {
                    "timestamp": str(record["timestamp"]),
                    "action_id": str(record["action_id"]),
                    "proposal_id": (
                        None
                        if pd.isna(record.get("proposal_id"))
                        else str(record["proposal_id"])
                    ),
                    "zone": CONTROLLED_ZONE,
                    "requested_setpoint_c": record["requested_setpoint_c"],
                    "approved_setpoint_c": record["approved_setpoint_c"],
                    "applied_setpoint_c": record["applied_setpoint_c"],
                    "observed_setpoint_c": record["observed_setpoint_c"],
                    "safety_level": record["safety_level"],
                    "fallback": bool(record["fallback"]),
                    "rollback": bool(record["rollback"]),
                },
                expanded=False,
            )

    faults = pd.DataFrame(context.get("safety_run", {}).get("faults", []))
    streamlit.subheader("Deterministic exception outcomes")
    if faults.empty:
        streamlit.info("No Phase 9 fault-injection records are available.")
    else:
        if selected_filters:
            faults["category"] = faults["actual_outcome"].astype(str).map(_category)
            faults = faults.loc[faults["category"].isin(selected_filters)]
        streamlit.dataframe(
            faults[
                [
                    "scenario",
                    "expected_outcomes",
                    "actual_outcome",
                    "expected_rule",
                    "passed",
                ]
            ],
            hide_index=True,
        )
        streamlit.caption(
            "Fault-injection records are deterministic test scenarios and do not "
            "carry live timestamps or actuator writes."
        )


__all__ = ["FILTER_OPTIONS", "render_decisions"]
