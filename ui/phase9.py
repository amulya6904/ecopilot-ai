"""Streamlit page for Phase 9 deterministic safety supervision."""

from collections import Counter
import json
from pathlib import Path
from typing import Any

import pandas as pd

from energyplus.runtime_control.api_loader import inspect_runtime_availability
from energyplus.runtime_control.settings import PHASE8_SETTINGS
from safety.artifacts import REQUIRED_SAFETY_ARTIFACTS
from safety.fault_injection import run_fault_injection_suite
from safety.settings import SAFETY_SETTINGS
from scripts.run_phase9_safety_validation import run_validation


def _latest_run() -> tuple[Path | None, dict[str, Any], dict[str, Any]]:
    root = SAFETY_SETTINGS.resolve(SAFETY_SETTINGS.artifact_root)
    candidates = sorted(
        root.glob("*/run_metadata.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for metadata_path in candidates:
        try:
            metadata = json.loads(
                metadata_path.read_text(encoding="utf-8")
            )
            summary_path = metadata_path.parent / "summary.json"
            summary = (
                json.loads(summary_path.read_text(encoding="utf-8"))
                if summary_path.is_file()
                else {}
            )
            return metadata_path.parent, metadata, summary
        except (OSError, json.JSONDecodeError):
            continue
    return None, {}, {}


def phase9_complete() -> bool:
    root = SAFETY_SETTINGS.resolve(SAFETY_SETTINGS.artifact_root)
    for metadata_path in root.glob("*/run_metadata.json"):
        try:
            metadata = json.loads(
                metadata_path.read_text(encoding="utf-8")
            )
            summary = json.loads(
                (metadata_path.parent / "summary.json").read_text(
                    encoding="utf-8"
                )
            )
            faults = json.loads(
                (
                    metadata_path.parent
                    / "fault_injection_results.json"
                ).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            continue
        if (
            metadata.get("acceptance_checks_passed") is True
            and summary.get("classification")
            == "safety_supervised_energyplus_runtime_validation"
            and summary.get("safety_supervisor_enabled") is True
            and summary.get("deterministic_safety_authority") is True
            and summary.get("severe_count") == 0
            and summary.get("fatal_count") == 0
            and (
                metadata.get("energyplus_runtime_available") is not True
                or metadata.get("energyplus_runtime_executed") is True
            )
            and len(faults) == 22
            and all(item.get("passed") is True for item in faults)
        ):
            return True
    return False


def _load_json(directory: Path, name: str) -> Any:
    path = directory / name
    if not path.is_file():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _show_faults(st: Any, names: set[str] | None) -> None:
    results = run_fault_injection_suite()
    selected = (
        results
        if names is None
        else [item for item in results if item["scenario"] in names]
    )
    st.session_state["phase9_fault_results"] = selected


def _render_charts(
    st: Any,
    states: pd.DataFrame,
    decisions: list[dict[str, Any]],
    rollbacks: list[dict[str, Any]],
) -> None:
    st.subheader("Safety timelines")
    if not states.empty:
        temperature = pd.DataFrame(
            {
                "Indoor temperature": pd.to_numeric(
                    states.get("indoor_temperature_c"), errors="coerce"
                ),
                "Occupied minimum": (
                    SAFETY_SETTINGS.occupied_temperature_min_c
                ),
                "Occupied maximum": (
                    SAFETY_SETTINGS.occupied_temperature_max_c
                ),
            }
        )
        st.line_chart(
            temperature,
            y=[
                "Indoor temperature",
                "Occupied minimum",
                "Occupied maximum",
            ],
            width="stretch",
        )
        pmv = pd.DataFrame(
            {
                "PMV": pd.to_numeric(
                    states.get("pmv"), errors="coerce"
                ),
                "PMV minimum": SAFETY_SETTINGS.pmv_min,
                "PMV maximum": SAFETY_SETTINGS.pmv_max,
            }
        )
        if pmv["PMV"].notna().any():
            st.line_chart(pmv, width="stretch")
        else:
            st.info(
                "Genuine PMV is unavailable in this retained EnergyPlus model; "
                "the occupied-temperature proxy is shown explicitly."
            )
        demand = pd.DataFrame(
            {
                "Facility demand": pd.to_numeric(
                    states.get("facility_demand_kw"), errors="coerce"
                ),
                "Warning": SAFETY_SETTINGS.demand_warning_kw,
                "Critical": SAFETY_SETTINGS.demand_critical_kw,
            }
        )
        st.line_chart(demand, width="stretch")
    if decisions:
        setpoints = pd.DataFrame(
            {
                "Requested": [
                    item["requested_value_c"] for item in decisions
                ],
                "Approved": [
                    item.get("approved_value_c") for item in decisions
                ],
            }
        )
        st.line_chart(setpoints, width="stretch")
        counts = Counter(item["decision"] for item in decisions)
        st.bar_chart(
            pd.DataFrame(
                {
                    "Decision count": list(counts.values())
                },
                index=list(counts),
            ),
            width="stretch",
        )
    if rollbacks:
        st.dataframe(
            pd.DataFrame(rollbacks),
            hide_index=True,
            width="stretch",
        )


def render_phase9(st: Any) -> None:
    st.warning(
        "This phase validates deterministic safety intervention and recovery. "
        "It is not final optimization, a savings comparison, or production "
        "safety certification."
    )
    st.info(
        "Genuine PMV/PPD is unavailable in the retained model, so occupied "
        "temperature is the declared comfort proxy. Demand warning and critical "
        "thresholds are prototype project guardrails, not a site-commissioned limit.",
        icon=":material/info:",
    )
    availability = inspect_runtime_availability()
    directory, metadata, summary = _latest_run()

    st.subheader("Readiness")
    readiness = st.container(horizontal=True, border=True)
    readiness.metric("Supervisor", "Enabled")
    readiness.metric(
        "EnergyPlus runtime",
        "Ready" if availability.available else "Unavailable",
    )
    readiness.metric("Actuator", PHASE8_SETTINGS.controlled_zone)
    readiness.metric(
        "Comfort mode",
        summary.get("comfort_method", "Temperature proxy"),
    )
    readiness.metric(
        "PMV availability",
        "Available" if summary.get("pmv_available") else "Unavailable",
    )
    readiness.metric("Fallback", "Phase 5 baseline")
    readiness.metric(
        "Phase 9", "Complete" if phase9_complete() else "Not accepted"
    )

    st.subheader("Operational constraints")
    constraints = [
        (
            "Occupied temperature",
            f"{SAFETY_SETTINGS.occupied_temperature_min_c:g}–"
            f"{SAFETY_SETTINGS.occupied_temperature_max_c:g} °C",
        ),
        (
            "PMV range",
            f"{SAFETY_SETTINGS.pmv_min:g} to "
            f"{SAFETY_SETTINGS.pmv_max:g}",
        ),
        ("PPD warning", f"{SAFETY_SETTINGS.ppd_warning_percent:g}%"),
        (
            "Cooling setpoint",
            f"{SAFETY_SETTINGS.minimum_cooling_setpoint_c:g}–"
            f"{SAFETY_SETTINGS.maximum_cooling_setpoint_c:g} °C",
        ),
        (
            "Maximum delta",
            f"{SAFETY_SETTINGS.maximum_setpoint_change_c:g} °C",
        ),
        (
            "Minimum deadband",
            f"{SAFETY_SETTINGS.minimum_heating_cooling_deadband_c:g} °C",
        ),
        (
            "Demand warning",
            f"{SAFETY_SETTINGS.demand_warning_kw:g} kW",
        ),
        (
            "Demand critical",
            f"{SAFETY_SETTINGS.demand_critical_kw:g} kW",
        ),
        (
            "Telemetry freshness",
            f"{SAFETY_SETTINGS.maximum_telemetry_age_seconds:g} s",
        ),
    ]
    cards = st.container(horizontal=True, horizontal_alignment="distribute")
    for label, value in constraints:
        with cards.container(border=True):
            st.metric(label, value)
    st.caption(
        "Demand thresholds are prototype project thresholds pending final "
        "calibration."
    )

    controls = st.container(horizontal=True)
    st.caption("Expected duration: approximately 1–3 minutes.")
    if controls.button(
        "Run Safety Test Suite",
        type="primary",
        width="stretch",
    ):
        with st.status(
            "Running deterministic and EnergyPlus safety validation",
            expanded=True,
        ) as status:
            result = run_validation()
            st.session_state["phase9_validation_result"] = result
            status.update(
                label=(
                    "Phase 9 acceptance passed"
                    if result["success"]
                    else "Phase 9 acceptance failed"
                ),
                state="complete" if result["success"] else "error",
            )
        directory, metadata, summary = _latest_run()
    if controls.button("Refresh Verified Results", width="stretch"):
        directory, metadata, summary = _latest_run()

    if directory is None:
        st.info(
            "No Phase 9 artifact exists yet. Run the validation or a fault "
            "scenario."
        )
        return

    states_path = directory / "safety_state_snapshots.csv"
    states = (
        pd.read_csv(states_path)
        if states_path.is_file() and states_path.stat().st_size
        else pd.DataFrame()
    )
    decisions = _load_json(directory, "safety_decisions.json")
    proposals = _load_json(directory, "proposed_actions.json")
    post = _load_json(directory, "post_action_verification.json")
    rollbacks = _load_json(directory, "rollback_events.json")
    emergencies = _load_json(directory, "emergency_events.json")
    rules = _load_json(directory, "safety_rule_results.json")

    latest_state = states.iloc[-1].to_dict() if not states.empty else {}
    latest_proposal = proposals[-1] if proposals else {}
    latest_decision = decisions[-1] if decisions else {}
    latest_post = post[-1] if post else {}
    detail_columns = st.columns(2)
    with detail_columns[0].container(border=True):
        st.subheader("Current safety state")
        st.json(
            {
                "zone": latest_state.get("zone_name"),
                "occupancy": latest_state.get("occupancy_value"),
                "temperature_c": latest_state.get(
                    "indoor_temperature_c"
                ),
                "pmv": latest_state.get("pmv"),
                "ppd_percent": latest_state.get("ppd_percent"),
                "cooling_setpoint_c": latest_state.get(
                    "cooling_setpoint_c"
                ),
                "heating_setpoint_c": latest_state.get(
                    "heating_setpoint_c"
                ),
                "demand_kw": latest_state.get("facility_demand_kw"),
                "actuator_valid": latest_state.get("actuator_valid"),
                "telemetry_age_seconds": latest_state.get(
                    "telemetry_age_seconds"
                ),
            }
        )
    with detail_columns[1].container(border=True):
        st.subheader("Proposed action")
        st.json(
            {
                "source": latest_proposal.get("source_type"),
                "requested_value_c": latest_proposal.get(
                    "requested_value_c"
                ),
                "objective": latest_proposal.get("objective"),
                "evidence": latest_proposal.get("evidence_references"),
                "reason": latest_proposal.get("reason"),
            }
        )
    result_columns = st.columns(2)
    with result_columns[0].container(border=True):
        st.subheader("Safety result")
        st.json(
            {
                "decision": latest_decision.get("decision"),
                "safety_level": latest_decision.get("safety_level"),
                "approved_or_clamped_value_c": latest_decision.get(
                    "approved_value_c"
                ),
                "violated_rules": [
                    item.get("rule_id")
                    for item in latest_decision.get("violated_rules", [])
                ],
                "warnings": [
                    item.get("rule_id")
                    for item in latest_decision.get("warnings", [])
                ],
                "fallback_required": latest_decision.get(
                    "fallback_required"
                ),
                "operator_review_required": latest_decision.get(
                    "operator_review_required"
                ),
            }
        )
    with result_columns[1].container(border=True):
        st.subheader("Post-action verification")
        st.json(
            {
                "applied_value_c": latest_post.get("approved_value_c"),
                "observed_value_c": latest_post.get("observed_value_c"),
                "temperature_response_c": latest_post.get(
                    "observed_temperature_c"
                ),
                "pmv_response": latest_post.get("observed_pmv"),
                "demand_response_kw": latest_post.get(
                    "observed_demand_kw"
                ),
                "verified_safe": latest_post.get("verified_safe"),
                "rollback_required": latest_post.get(
                    "rollback_required"
                ),
            }
        )

    st.subheader("Fault injection")
    fault_buttons = st.container(horizontal=True)
    scenarios = {
        "Comfort risk": {"PMV high"},
        "Stale telemetry": {"Stale telemetry"},
        "Demand critical": {"Demand critical"},
        "Deadband conflict": {"Deadband conflict"},
        "Oscillation": {"Oscillation"},
    }
    for label, names in scenarios.items():
        if fault_buttons.button(label, width="stretch"):
            _show_faults(st, names)
    if fault_buttons.button("Full suite", width="stretch"):
        _show_faults(st, None)
    fault_results = st.session_state.get("phase9_fault_results")
    if fault_results:
        st.dataframe(
            pd.DataFrame(fault_results),
            hide_index=True,
            width="stretch",
        )

    _render_charts(st, states, decisions, rollbacks)
    st.subheader("Classification")
    st.json(
        {
            "classification": summary.get("classification"),
            "safety_supervisor_enabled": summary.get(
                "safety_supervisor_enabled"
            ),
            "deterministic_safety_authority": summary.get(
                "deterministic_safety_authority"
            ),
            "comfort_method": summary.get("comfort_method"),
            "pmv_used": summary.get("pmv_available"),
            "temperature_proxy_used": not summary.get("pmv_available", False),
            "rollback_tested": bool(rollbacks),
            "emergency_fallback_tested": bool(emergencies),
            "final_optimization_result": "No",
            "savings_result": "No",
        }
    )
    st.subheader("Download safety evidence")
    downloads = st.container(horizontal=True)
    requested = {
        "safety_state_snapshots.csv",
        "safety_decisions.json",
        "safety_rule_results.json",
        "rollback_events.json",
        "emergency_events.json",
        "fault_injection_results.json",
        "summary.json",
    }
    for name in REQUIRED_SAFETY_ARTIFACTS:
        if name not in requested:
            continue
        path = directory / name
        if path.is_file():
            downloads.download_button(
                name,
                data=path.read_bytes(),
                file_name=name,
                mime=(
                    "text/csv"
                    if name.endswith(".csv")
                    else "application/json"
                ),
                width="stretch",
            )


__all__ = ["phase9_complete", "render_phase9"]
