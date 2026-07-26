"""Default Phase 12 Command Center product page."""

from typing import Any

import pandas as pd

from ui.components import status_badge
from ui.formatting import (
    format_carbon,
    format_cost,
    format_demand,
    format_energy,
    format_percent,
)

from .charts import filtered_line_chart
from .components import (
    closed_loop_pipeline,
    decision_spotlight,
    kpi_card,
    product_header,
    safe_page_error,
    system_status_strip,
)
from .data import (
    CONTROLLED_ZONE,
    DEMO_MODE_REPLAY,
    ArtifactLoadError,
    load_comparison_csv,
    load_demo_context,
    load_zone_telemetry,
)


def _zone_status(row: pd.Series) -> str:
    occupancy = pd.to_numeric(row.get("occupancy_controlled"), errors="coerce")
    temperature = pd.to_numeric(
        row.get("indoor_temperature_c_controlled"),
        errors="coerce",
    )
    if pd.isna(temperature):
        return "Telemetry unavailable"
    if pd.isna(occupancy) or occupancy <= 0:
        return "Unoccupied"
    if temperature < 22:
        return "Below configured range"
    if temperature > 25:
        return "Above configured range"
    return "Comfortable"


def _render_zone_preview(streamlit: Any, context: dict[str, Any]) -> None:
    zones = load_zone_telemetry(index=context["index"])
    controlled = zones.loc[zones["energyplus_zone_name"].eq(CONTROLLED_ZONE)]
    occupied = controlled.loc[
        pd.to_numeric(controlled["occupancy_controlled"], errors="coerce").fillna(0)
        > 0
    ]
    timestamp = (
        occupied["timestamp"].dropna().max()
        if not occupied.empty
        else zones["timestamp"].dropna().max()
    )
    snapshot = zones.loc[zones["timestamp"].eq(timestamp)].copy()

    streamlit.subheader("Building status")
    streamlit.caption(
        f"Selected verified artifact timestamp · {timestamp} · EnergyPlus telemetry"
    )
    with streamlit.container(horizontal=True, gap="small"):
        for _, row in snapshot.iterrows():
            zone = str(row["energyplus_zone_name"])
            controlled_zone = zone == CONTROLLED_ZONE
            with streamlit.container(
                border=True,
                key=f"command-zone-{zone.lower()}",
            ):
                streamlit.caption(
                    f"{'CONTROLLED' if controlled_zone else 'MONITORED ONLY'} · "
                    f"{row.get('zone_role_controlled', 'zone')}"
                )
                streamlit.markdown(
                    f"**{row.get('display_zone_name_controlled', zone)}**"
                )
                streamlit.caption(zone)
                temperature = row.get("indoor_temperature_c_controlled")
                setpoint = row.get("cooling_setpoint_c_controlled")
                streamlit.metric(
                    "Temperature",
                    (
                        f"{float(temperature):.1f} °C"
                        if pd.notna(temperature)
                        else "Unavailable"
                    ),
                )
                streamlit.caption(
                    "Cooling setpoint · "
                    + (
                        f"{float(setpoint):.1f} °C"
                        if pd.notna(setpoint) and float(setpoint) > 0
                        else "Not applicable"
                    )
                )
                status_badge(
                    streamlit,
                    _zone_status(row),
                    status=(
                        "verified"
                        if _zone_status(row) == "Comfortable"
                        else "info"
                        if _zone_status(row) == "Unoccupied"
                        else "warning"
                    ),
                )
    runtime = context.get("runtime", {}).get("summary", {})
    streamlit.caption("SPACE1-1 · latest verified controlled-run lifecycle")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Baseline", runtime.get("baseline_setpoint_c")),
            ("Requested", runtime.get("requested_setpoint_c")),
            ("Approved", runtime.get("approved_setpoint_c")),
            ("Applied", runtime.get("applied_setpoint_c")),
            ("Observed after reset", runtime.get("observed_setpoint_c")),
        ):
            streamlit.metric(
                label,
                f"{float(value):.1f} °C"
                if isinstance(value, (int, float))
                else "Unavailable",
                border=True,
            )
    status_badge(
        streamlit,
        "Deterministic safety authority · actuator injection verified",
        status="verified",
    )


def _render_chart_preview(streamlit: Any, context: dict[str, Any]) -> None:
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
    preview = energy.loc[
        energy["timestamp"].between(
            center - pd.Timedelta(days=14),
            center + pd.Timedelta(days=14),
        )
    ]
    streamlit.subheader("Measured impact preview")
    filtered_line_chart(
        streamlit,
        preview,
        series={
            "baseline_cumulative_energy_kwh": "Fixed-schedule baseline",
            "controlled_cumulative_energy_kwh": "Safety-supervised controlled",
        },
        y_title="Cumulative facility electricity (kWh)",
        source="Phase 10 energy_comparison.csv · selected difference window",
        zero=False,
    )


def _render_decision_preview(streamlit: Any, context: dict[str, Any]) -> None:
    phase7 = context.get("phase7", {})
    metadata = phase7.get("metadata", {})
    proposal = phase7.get("proposal", {})
    validation = phase7.get("validation", {})
    with streamlit.container(border=True, key="decision-preview"):
        heading, state = streamlit.columns([4, 1], vertical_alignment="center")
        heading.caption("LATEST AI DECISION · VERIFIED REPLAY")
        heading.subheader(
            f"{proposal.get('display_zone_name', 'Open Office')} · "
            f"{proposal.get('energyplus_zone_name', CONTROLLED_ZONE)}"
        )
        state.markdown("**ADVISORY**")
        status_badge(
            state,
            "Schema valid" if validation.get("valid") else "Review required",
            status="verified" if validation.get("valid") else "warning",
        )
        streamlit.write(
            proposal.get(
                "reason",
                "No verified Phase 7 advisory reason is available.",
            )
        )
        with streamlit.container(horizontal=True, gap="small"):
            for label, value in (
                ("Current", proposal.get("current_setpoint_c")),
                ("Proposed", proposal.get("proposed_setpoint_c")),
                ("Confidence", proposal.get("confidence")),
                ("Applied", "No · advisory only"),
            ):
                with streamlit.container(border=True):
                    streamlit.caption(label.upper())
                    if isinstance(value, (int, float)) and label != "Confidence":
                        streamlit.markdown(f"**{value:.1f} °C**")
                    elif label == "Confidence" and isinstance(value, (int, float)):
                        streamlit.markdown(f"**{value:.0%}**")
                    else:
                        streamlit.markdown(f"**{value or 'Unavailable'}**")
        streamlit.caption(
            f"Saved run · {metadata.get('agent_run_id', 'Unavailable')} · qwen3:4b"
        )


def _render_closed_loop_counts(
    streamlit: Any,
    actions: pd.DataFrame,
) -> None:
    streamlit.subheader("Latest verified closed-loop replay")
    if actions.empty:
        streamlit.info("No live session is active.")
        streamlit.caption("Latest verified closed-loop replay is available.")
        return
    decisions = actions.get("decision", pd.Series(dtype="string")).astype(str)
    counts = (
        ("Proposed", len(actions)),
        ("Approved", int(decisions.isin({"approve", "approve_with_clamp"}).sum())),
        ("Rejected", int(decisions.isin({"reject", "hold"}).sum())),
        (
            "Applied",
            int(actions.get("applied_setpoint_c", pd.Series(dtype=float)).notna().sum()),
        ),
        (
            "Fallback",
            int(actions.get("fallback", pd.Series(dtype=bool)).fillna(False).sum()),
        ),
        (
            "Rollback",
            int(actions.get("rollback", pd.Series(dtype=bool)).fillna(False).sum()),
        ),
    )
    with streamlit.container(
        horizontal=True,
        gap="small",
        key="closed-loop-counts",
    ):
        for label, value in counts:
            streamlit.metric(label, f"{value:,}", border=True)
    streamlit.caption(
        "Source · latest verified Phase 10 action_summary.csv · no live session claimed"
    )


def render_command_center(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    try:
        context = load_demo_context()
        summary = context["summary"]
        safety = context.get("safety_run", {}).get("summary", {})
        runtime = context.get("runtime", {}).get("summary", {})
        actions = load_comparison_csv(
            "action_summary.csv",
            index=context["index"],
        )
    except ArtifactLoadError as exc:
        product_header(
            streamlit,
            title="EcoPilot AI",
            subtitle="Safety-Supervised Autonomous Building Control",
            eyebrow="Smart building command center",
            mode=mode,
        )
        safe_page_error(
            streamlit,
            title="Verified comparison unavailable",
            message=exc.public_message,
            next_step=(
                "Run the documented Phase 10 comparison and reproducibility "
                "commands, then refresh this page."
            ),
            diagnostics=exc.diagnostics,
        )
        return

    product_header(
        streamlit,
        title="EcoPilot AI",
        subtitle="Safety-Supervised Autonomous Building Control",
        eyebrow="Smart building command center",
        mode=mode,
    )
    streamlit.caption("Conservative single-zone EnergyPlus proof of concept")

    system_status_strip(
        streamlit,
        (
            ("EnergyPlus", "Verified", "26.1 · saved official run"),
            ("MCP tools", "Ready", "16 tools · 6 resources"),
            (
                "qwen3:4b",
                "Artifact replay" if mode == DEMO_MODE_REPLAY else "On demand",
                "local · no automatic request",
            ),
            ("Safety", "Active", "deterministic final authority"),
            ("Actuator", "Verified", CONTROLLED_ZONE),
            ("Comparison", "Reproducible", str(summary["comparison_id"])),
        ),
    )

    streamlit.subheader("Official annual outcome")
    with streamlit.container(horizontal=True, gap="small", key="command-kpis"):
        kpi_card(
            streamlit,
            label="Verified facility-energy reduction",
            value=format_energy(summary["energy_reduction_kwh"], compact=True),
            note="Aligned annual comparison",
            badge="Verified",
        )
        kpi_card(
            streamlit,
            label="Reproducible annual reduction",
            value=format_percent(summary["energy_reduction_percent"], 4),
            note="One-zone conservative policy",
        )
        kpi_card(
            streamlit,
            label="Comfort-proxy change",
            value=(
                f"{summary['comfort_metrics']['comfort_change_percent_points']:+.3f} pp"
            ),
            note="Occupied-temperature proxy",
        )
        kpi_card(
            streamlit,
            label="Peak demand",
            value=format_demand(summary["controlled_peak_demand_kw"]),
            note="Essentially unchanged",
        )
        kpi_card(
            streamlit,
            label="Safety scenarios",
            value="22/22",
            note="Verified Phase 9 fault suite",
            badge="Verified",
        )
        kpi_card(
            streamlit,
            label="Severe / fatal errors",
            value=f"{summary['severe_count']} / {summary['fatal_count']}",
            note="Official comparison",
            badge="Verified",
        )

    with streamlit.container(horizontal=True, gap="small"):
        with streamlit.container(key="primary-action"):
            streamlit.page_link(
                "app_pages/guided_demo.py",
                label="Start guided demo",
                icon=":material/play_arrow:",
                width="content",
            )
        streamlit.page_link(
            "app_pages/analytics.py",
            label="Open analytics",
            icon=":material/analytics:",
            width="content",
        )
        streamlit.page_link(
            "app_pages/ai_copilot.py",
            label="Ask EcoPilot",
            icon=":material/chat:",
            width="content",
        )

    _render_decision_preview(streamlit, context)
    _render_closed_loop_counts(streamlit, actions)

    streamlit.caption("COMPACT CLOSED-LOOP PIPELINE")
    phase7 = context.get("phase7", {})
    metadata = phase7.get("metadata", {})
    proposal = phase7.get("proposal", {})
    llm_runtime = context.get("llm_runtime", {}).get("summary", {})
    comparison_timestamp = str(summary["comparison_id"]).split(
        "-phase10",
        1,
    )[0]
    agent_timestamp = str(metadata.get("agent_run_id", "Unavailable")).split(
        "-",
        1,
    )[0]
    runtime_timestamp = str(
        context["controlled_summary"].get("run_id", "Unavailable")
    ).split("-phase10", 1)[0]
    closed_loop_pipeline(
        streamlit,
        (
            {
                "name": "EnergyPlus telemetry",
                "output": "Annual evidence loaded",
                "status": "Verified",
                "source": "Phase 10 aligned telemetry",
                "timestamp": comparison_timestamp,
                "duration": "8,760 hourly intervals",
            },
            {
                "name": "Advisory",
                "output": (
                    f"{proposal.get('current_setpoint_c', '—')} → "
                    f"{proposal.get('proposed_setpoint_c', '—')} °C"
                ),
                "status": "Advisory",
                "status_kind": "warning",
                "source": "qwen3:4b · 5 MCP tools",
                "timestamp": agent_timestamp,
                "duration": (
                    f"{metadata.get('final_decision_generation_ms', 0) / 1000:.1f} s"
                ),
            },
            {
                "name": "Safety",
                "output": "Deterministic authority",
                "status": "Active",
                "source": "Phase 9 · 22/22 scenarios",
            },
            {
                "name": "Apply and verify",
                "output": "Reset and fallback protected",
                "status": "Verified",
                "source": f"Phase 8 Runtime API · {CONTROLLED_ZONE}",
                "timestamp": runtime_timestamp,
                "duration": f"{runtime.get('actuator_write_count', 0):,} writes",
            },
        ),
    )

    _render_zone_preview(streamlit, context)
    with streamlit.expander(
        "Full AI decision and runtime evidence",
        icon=":material/data_object:",
    ):
        decision_spotlight(streamlit, context)

    streamlit.subheader("Additional verified impact")
    with streamlit.container(horizontal=True, gap="small"):
        kpi_card(
            streamlit,
            label="Controlled energy",
            value=format_energy(summary["controlled_energy_kwh"]),
            note="Official EnergyPlus",
            badge="Verified",
        )
        kpi_card(
            streamlit,
            label="Cost reduction",
            value=format_cost(
                summary["cost_metrics"]["absolute_cost_reduction"],
                summary["cost_metrics"]["currency"],
            ),
            note="Derived from configured assumption",
        )
        kpi_card(
            streamlit,
            label="Carbon reduction",
            value=format_carbon(
                summary["carbon_metrics"]["absolute_carbon_reduction_kg"]
            ),
            note="Derived from configured assumption",
        )
    _render_chart_preview(streamlit, context)

    streamlit.info(
        str(summary["exact_approved_statement"]),
        icon=":material/verified:",
    )
    streamlit.caption(
        "Whole-building effect is small because one zone is controlled under "
        "strict safety limits. PMV is unavailable; occupied-temperature proxy "
        "is used. Cost and carbon are derived from configured assumptions."
    )


__all__ = ["render_command_center"]
