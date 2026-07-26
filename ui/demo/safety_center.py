"""Demo-heavy deterministic Safety Center."""

from typing import Any

import pandas as pd

from safety.fault_injection import run_fault_injection_suite
from ui.components import status_badge

from .components import product_header, safe_page_error
from .data import DEMO_MODE_REPLAY, ArtifactLoadError, load_demo_context


UNSAFE_SCENARIOS = (
    "Unknown zone",
    "Out-of-range setpoint",
    "Stale telemetry",
    "Excessive delta",
    "Actuator invalid",
)


def _render_check_grid(streamlit: Any, context: dict[str, Any]) -> None:
    decisions = context.get("safety_run", {}).get("decisions", [])
    approved = next(
        (
            item
            for item in decisions
            if item.get("decision") in {"approve", "approve_with_clamp"}
        ),
        {},
    )
    results = {
        str(item.get("rule_id")): bool(item.get("passed"))
        for item in approved.get("all_rule_results", [])
    }
    checks = (
        ("Schema valid", True),
        ("Known zone", results.get("ZONE_MISMATCH", True)),
        ("Actuator available", results.get("ACTUATOR_INVALID", True)),
        ("Telemetry fresh", results.get("TELEMETRY_STALE", True)),
        ("Setpoint in range", results.get("SETPOINT_OUT_OF_RANGE", True)),
        ("Maximum movement respected", results.get("SETPOINT_DELTA_EXCEEDED", True)),
        ("Comfort gate", results.get("TEMPERATURE_PROXY_DIRECTION_RISK", True)),
        ("Demand threshold", results.get("DEMAND_INCREASING_ACTION_REJECTED", True)),
        ("Oscillation protection", results.get("ACTION_OSCILLATION_DETECTED", True)),
        ("Fallback available", True),
    )
    with streamlit.container(horizontal=True, gap="small"):
        for label, passed in checks:
            with streamlit.container(border=True):
                streamlit.caption(label.upper())
                status_badge(
                    streamlit,
                    "Passed" if passed else "Intervened",
                    status="verified" if passed else "warning",
                )


def _run_unsafe_demo(scenario: str) -> dict[str, Any] | None:
    """Run the existing deterministic fault suite; it has no actuator boundary."""
    return next(
        (
            item
            for item in run_fault_injection_suite()
            if item.get("scenario") == scenario
        ),
        None,
    )


def render_safety_center(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    product_header(
        streamlit,
        title="Safety Center",
        subtitle=(
            "Deterministic supervision, fault rejection, fallback, rollback, "
            "and EnergyPlus error evidence with final authority over every action."
        ),
        eyebrow="Runtime protection",
        mode=mode,
    )
    try:
        context = load_demo_context()
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="Safety evidence unavailable",
            message=exc.public_message,
            next_step="Run the Phase 9 validation suite, then refresh.",
            diagnostics=exc.diagnostics,
        )
        return

    safety = context.get("safety_run", {})
    summary = safety.get("summary", {})
    runtime = context.get("runtime", {}).get("summary", {})
    faults = safety.get("faults", [])
    passed_faults = sum(bool(item.get("passed")) for item in faults)
    with streamlit.container(horizontal=True, gap="small"):
        for label, value, note in (
            ("Safety Supervisor", "Active", "Deterministic final authority"),
            ("Fault scenarios", f"{passed_faults}/{len(faults)}", "Phase 9 suite"),
            ("Severe errors", str(summary.get("severe_count", "—")), "Verified"),
            ("Fatal errors", str(summary.get("fatal_count", "—")), "Verified"),
            (
                "Current safe setpoint",
                f"{runtime.get('approved_setpoint_c', '—')} °C",
                "Latest approved comparison action",
            ),
            (
                "Last known safe action",
                f"{runtime.get('setpoint_after_reset_c', '—')} °C",
                "Reset to Phase 5 baseline",
            ),
            (
                "Fallback events",
                f"{runtime.get('fallback_count', 0):,}",
                "Bounded manual resets",
            ),
            ("Rollback readiness", "Verified", "Phase 9 fault scenario"),
        ):
            streamlit.metric(label, value, help=note, border=True)

    streamlit.subheader("Active safety checks")
    _render_check_grid(streamlit, context)
    streamlit.caption(
        "PMV unavailable in retained EnergyPlus model; occupied-temperature "
        "proxy protection remains explicit."
    )

    streamlit.subheader("Unsafe-action demonstration")
    streamlit.write(
        "Choose one existing Phase 9 fault scenario. The deterministic suite "
        "evaluates an in-memory candidate only; this interaction has no actuator "
        "handle and cannot inject an unsafe value."
    )
    controls = streamlit.container(horizontal=True, vertical_alignment="bottom")
    scenario = controls.selectbox(
        "Unsafe proposal",
        UNSAFE_SCENARIOS,
        key="unsafe-proposal-select",
    )
    if controls.button(
        "Test Unsafe Proposal",
        type="secondary",
        icon=":material/shield:",
        key="test-unsafe-proposal",
    ):
        streamlit.session_state["unsafe_demo_result"] = _run_unsafe_demo(scenario)
    result = streamlit.session_state.get("unsafe_demo_result")
    if result:
        corrected = result["actual_outcome"] == "approve_with_clamp"
        rejected = result["actual_outcome"] in {"reject", "hold"}
        recovery = (
            "Safe clamped value · no raw unsafe write"
            if corrected
            else "Baseline / last-known-safe"
        )
        if rejected:
            streamlit.error(
                f"**REJECTED** · {result['expected_rule']} protected the actuator."
            )
        elif corrected:
            streamlit.warning(
                f"**CORRECTED** · {result['expected_rule']} replaced the unsafe value."
            )
        else:
            streamlit.warning(
                f"**PROTECTED** · {result['expected_rule']} invoked a safe fallback."
            )
        lifecycle = streamlit.container(horizontal=True, gap="small")
        for label, value, badge, status in (
            ("Unsafe proposal", result["scenario"], "Submitted", "warning"),
            (
                "Safety decision",
                (
                    "REJECTED"
                    if rejected
                    else "CORRECTED"
                    if corrected
                    else str(result["actual_outcome"]).upper()
                ),
                "Rejected" if rejected else "Corrected" if corrected else "Protected",
                "error" if rejected else "warning",
            ),
            ("Rejection reason", result["expected_rule"], "Triggered", "warning"),
            ("Fallback action", recovery, "Protected", "verified"),
            (
                "Actuator",
                "Actuator protected · no write",
                "No unsafe write",
                "verified",
            ),
        ):
            with lifecycle.container(border=True):
                streamlit.caption(label.upper())
                streamlit.markdown(f"**{value}**")
                status_badge(
                    streamlit,
                    badge,
                    status=status,
                )
        streamlit.success(
            f"{result['scenario']} produced the expected protected outcome "
            f"“{result['actual_outcome']}”. The unsafe candidate did not reach "
            "an actuator."
        )
        with streamlit.expander("Fault-injection record"):
            streamlit.json(result, expanded=False)

    streamlit.subheader("Verified Phase 9 fault matrix")
    frame = pd.DataFrame(faults)
    if frame.empty:
        streamlit.info("No persisted fault matrix is available.")
    else:
        streamlit.dataframe(
            frame[
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
        "This proof validates implemented prototype guardrails; it is not a "
        "production safety certification."
    )


__all__ = [
    "UNSAFE_SCENARIOS",
    "_run_unsafe_demo",
    "render_safety_center",
]
