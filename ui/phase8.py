"""Streamlit page for real Phase 8 Runtime API control validation."""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

import pandas as pd

from energyplus.runtime_control.actuator_discovery import (
    discover_available_actuators,
)
from energyplus.runtime_control.api_loader import inspect_runtime_availability
from energyplus.runtime_control.artifacts import REQUIRED_ARTIFACTS
from energyplus.runtime_control.orchestrator import (
    run_manual_validation,
    run_mock_closed_loop,
)
from energyplus.runtime_control.settings import PHASE8_SETTINGS


def _latest_run() -> tuple[Path | None, dict[str, Any] | None]:
    root = PHASE8_SETTINGS.resolve(PHASE8_SETTINGS.artifact_root)
    summaries = sorted(root.glob("*/summary.json"), reverse=True)
    for path in summaries:
        try:
            return path.parent, json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None, None


def phase8_complete() -> bool:
    root = PHASE8_SETTINGS.resolve(PHASE8_SETTINGS.artifact_root)
    for path in root.glob("*/summary.json"):
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            summary.get("success") is True
            and summary.get("mode") == "mock"
            and summary.get("classification")
            == "mock_agent_energyplus_closed_loop_validation"
            and summary.get("control_injection_verified") is True
            and summary.get("actuator_reset_verified") is True
            and summary.get("fallback_verified") is True
            and summary.get("severe_count") == 0
            and summary.get("fatal_count") == 0
        ):
            return True
    return False


def _execute(st: Any, label: str, function: Callable[[], Any]) -> None:
    with st.status(label, expanded=True) as status:
        try:
            result = function()
            st.session_state["phase8_result"] = result
            state = "complete" if result.success else "error"
            status.update(
                label=f"{label}: {'passed' if result.success else 'failed'}",
                state=state,
            )
        except Exception as exc:
            st.exception(exc)
            status.update(label=f"{label}: failed", state="error")


def render_phase8(st: Any) -> None:
    st.header("Phase 8 — Safe Closed-Loop EnergyPlus Control")
    st.warning(
        "This phase validates bounded control injection and fallback. It is not "
        "an optimization result and does not establish energy savings."
    )
    availability = inspect_runtime_availability()
    inventory_path = PHASE8_SETTINGS.resolve(
        PHASE8_SETTINGS.official_inventory_path
    )
    inventory: dict[str, Any] = {}
    if inventory_path.is_file():
        try:
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            inventory = {}
    selected = inventory.get("selected_actuator") or {}
    cards = st.columns(6)
    cards[0].metric(
        "Python API", "Ready" if availability.available else "Unavailable"
    )
    cards[1].metric("Controlled zone", PHASE8_SETTINGS.controlled_zone)
    cards[2].metric(
        "Maximum delta",
        f"{PHASE8_SETTINGS.maximum_setpoint_change_c:g} °C",
    )
    cards[3].metric("Fallback", "Reset to baseline")
    cards[4].metric("Real LLM default", "Disabled")
    cards[5].metric("Phase 8", "Complete" if phase8_complete() else "Incomplete")
    st.write(
        {
            "runtime_model": str(
                PHASE8_SETTINGS.resolve(PHASE8_SETTINGS.runtime_model_path)
            ),
            "selected_actuator": selected.get("identifier", "Not discovered"),
            "component_type": selected.get("component_type"),
            "control_type": selected.get("control_type"),
            "actuator_key": selected.get("actuator_key"),
            "fallback_policy": PHASE8_SETTINGS.fallback_policy,
            "real_llm_enabled_by_default": PHASE8_SETTINGS.enable_real_llm,
        }
    )
    if availability.readiness_issues:
        st.error("\n".join(availability.readiness_issues))

    st.subheader("Runtime validation controls")
    buttons = st.columns(4)
    if buttons[0].button("Discover Actuators", width="stretch"):
        with st.status("Running Runtime API discovery", expanded=True) as status:
            result = discover_available_actuators()
            st.session_state["phase8_discovery"] = result
            status.update(
                label=(
                    "Actuator discovery passed"
                    if result["success"] else "Actuator discovery failed"
                ),
                state="complete" if result["success"] else "error",
            )
    if buttons[1].button("Run Manual Actuator Test", width="stretch"):
        _execute(st, "Manual actuator validation", run_manual_validation)
    if buttons[2].button("Run Mock Closed Loop", width="stretch"):
        _execute(st, "Mock closed-loop validation", run_mock_closed_loop)
    llm_opt_in = st.checkbox(
        "Explicitly enable one real Phase 7 LLM advisory",
        value=False,
        help="Inference completes before EnergyPlus callbacks are registered.",
    )
    if buttons[3].button(
        "Run LLM-Assisted Closed Loop",
        disabled=not llm_opt_in,
        width="stretch",
    ):
        with st.status("Running opt-in LLM-assisted validation") as status:
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.run_phase8_closed_loop",
                    "--enable-real-llm",
                ],
                capture_output=True,
                text=True,
                timeout=PHASE8_SETTINGS.llm_timeout_seconds + 600,
                check=False,
            )
            st.code(process.stdout or process.stderr)
            status.update(
                label=(
                    "LLM-assisted validation passed"
                    if process.returncode == 0
                    else "LLM-assisted validation failed"
                ),
                state="complete" if process.returncode == 0 else "error",
            )

    directory, summary = _latest_run()
    if directory is None or summary is None:
        st.info("No Phase 8 runtime artifact exists yet.")
        return
    st.subheader("Latest runtime evidence")
    values = st.columns(5)
    values[0].metric(
        "Baseline", f"{summary.get('baseline_setpoint_c', '—')} °C"
    )
    values[1].metric(
        "Requested", f"{summary.get('requested_setpoint_c', '—')} °C"
    )
    values[2].metric(
        "Approved", f"{summary.get('approved_setpoint_c', '—')} °C"
    )
    values[3].metric(
        "Applied", f"{summary.get('applied_setpoint_c', '—')} °C"
    )
    values[4].metric(
        "Observed", f"{summary.get('observed_setpoint_c', '—')} °C"
    )
    st.json(
        {
            "reset_verified": summary.get("actuator_reset_verified"),
            "fallback_verified": summary.get("fallback_verified"),
            "severe_count": summary.get("severe_count"),
            "fatal_count": summary.get("fatal_count"),
            "classification": summary.get("classification"),
            "control_injection_verified": summary.get(
                "control_injection_verified"
            ),
            "closed_loop_validation_complete": summary.get("success"),
            "real_llm_used": summary.get("real_llm_used"),
            "final_optimization_result": "No",
            "savings_result": "No",
        }
    )
    if summary.get("mode") == "phase7_llm":
        if summary.get("fallback_used"):
            st.warning(
                "LLM action rejected; deterministic runtime fallback used: "
                f"{summary.get('fallback_reason') or summary.get('llm_error_code')}"
            )
        st.subheader("LLM adapter diagnostics")
        st.json(
            {
                "live_current_setpoint_c": summary.get(
                    "baseline_setpoint_c"
                ),
                "raw_llm_requested_setpoint_c": summary.get(
                    "raw_llm_requested_setpoint_c"
                ),
                "normalized_requested_setpoint_c": summary.get(
                    "normalized_requested_setpoint_c"
                ),
                "normalization_applied": summary.get(
                    "normalization_applied"
                ),
                "normalization_reason": summary.get(
                    "normalization_reason"
                ),
                "fallback_action_setpoint_c": summary.get(
                    "fallback_action_setpoint_c"
                ),
                "fallback_reason": summary.get("fallback_reason"),
                "llm_error_code": summary.get("llm_error_code"),
                "llm_error_message": summary.get("llm_error_message"),
                "llm_action_used": summary.get("llm_action_used"),
                "fallback_used": summary.get("fallback_used"),
            }
        )
    handles_path = directory / "handle_registry.json"
    if handles_path.is_file():
        st.subheader("Variable, meter, and actuator handles")
        st.json(json.loads(handles_path.read_text(encoding="utf-8")))
    telemetry_path = directory / "telemetry.csv"
    applied_path = directory / "applied_actions.csv"
    if telemetry_path.is_file() and telemetry_path.stat().st_size:
        telemetry = pd.read_csv(telemetry_path)
        st.subheader("Telemetry timeline")
        st.dataframe(telemetry, hide_index=True, width="stretch")
    if applied_path.is_file() and applied_path.stat().st_size:
        st.subheader("Action timeline")
        st.dataframe(
            pd.read_csv(applied_path), hide_index=True, width="stretch"
        )
    st.subheader("Download artifacts")
    columns = st.columns(3)
    for index, name in enumerate(REQUIRED_ARTIFACTS):
        path = directory / name
        if path.is_file():
            columns[index % 3].download_button(
                name,
                data=path.read_bytes(),
                file_name=name,
                mime="text/csv" if name.endswith(".csv") else "application/json",
                width="stretch",
            )


__all__ = ["phase8_complete", "render_phase8"]
