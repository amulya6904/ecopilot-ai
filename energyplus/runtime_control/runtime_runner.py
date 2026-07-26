"""Run one real EnergyPlus Python API closed-loop validation."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from energyplus.adapter.error_parser import parse_energyplus_error_file
from safety.artifacts import SafetyArtifacts
from safety.audit import SafetyAuditLog

from .action_provider import ActionProvider
from .actuator_discovery import (
    ActuatorDescriptor,
    discover_available_actuators,
)
from .api_loader import load_energyplus_api
from .artifacts import Phase8Artifacts
from .audit import RuntimeAuditLog
from .callbacks import RuntimeCallbacks
from .settings import PHASE8_SETTINGS, Phase8Settings
from .variable_discovery import request_runtime_variables


@dataclass(frozen=True)
class Phase8RunResult:
    success: bool
    exit_code: int
    mode: str
    classification: str
    artifact_directory: Path
    summary: dict[str, Any]


def _selected_descriptor(inventory: dict[str, Any]) -> ActuatorDescriptor:
    selected = inventory.get("selected_actuator")
    if not isinstance(selected, dict):
        raise RuntimeError("No confirmed Phase 8 actuator was selected.")
    return ActuatorDescriptor(
        what=str(selected["what"]),
        component_type=str(selected["component_type"]),
        control_type=str(selected["control_type"]),
        actuator_key=str(selected["actuator_key"]),
        unit=str(selected["unit"]),
    )


def run_phase8_runtime(
    provider: ActionProvider,
    *,
    mode: str,
    classification: str,
    real_llm_used: bool = False,
    inventory: dict[str, Any] | None = None,
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> Phase8RunResult:
    inventory_result = inventory or discover_available_actuators(settings)
    if not inventory_result.get("success"):
        raise RuntimeError(
            "Runtime actuator discovery failed: "
            + "; ".join(inventory_result.get("errors", []))
        )
    actuator = _selected_descriptor(inventory_result)
    api, availability = load_energyplus_api(settings)
    if api is None or not availability.available:
        raise RuntimeError(
            "EnergyPlus Python API unavailable: "
            + "; ".join(availability.readiness_issues)
        )
    artifacts = Phase8Artifacts(mode, settings=settings)
    safety_artifacts = SafetyArtifacts(
        "energyplus-runtime",
        run_id=artifacts.run_id,
    )
    artifacts.inventory = inventory_result
    audit = RuntimeAuditLog(settings=settings)
    callback_handler = RuntimeCallbacks(
        api,
        provider,
        actuator,
        artifacts,
        audit,
        settings,
        safety_artifacts=safety_artifacts,
        safety_audit=SafetyAuditLog(),
    )
    state = api.state_manager.new_state()
    output = settings.resolve(settings.output_root) / artifacts.run_id
    output.mkdir(parents=True, exist_ok=False)
    request_runtime_variables(api.exchange, state, settings)
    callback_handler.register(state)
    args = [
        "-d",
        str(output),
        "-w",
        str(settings.resolve(settings.weather_file_path)),
        str(settings.resolve(settings.runtime_model_path)),
    ]
    exit_code = -1
    try:
        exit_code = int(api.runtime.run_energyplus(state, args))
    finally:
        api.state_manager.delete_state(state)
    error_summary = parse_energyplus_error_file(output / "eplusout.err")
    artifacts.runtime_errors = [asdict(item) for item in error_summary.records]
    state_summary = callback_handler.state
    control_injection = (
        state_summary.applications > 0
        and bool(getattr(provider, "override_observed", False)
                 or getattr(provider, "change_observed", False))
    )
    observed_change = bool(
        getattr(provider, "override_observed", False)
        or getattr(provider, "change_observed", False)
    )
    reset_verified = bool(getattr(provider, "reset_observed", False))
    fallback_verified = bool(
        getattr(provider, "fallback_observed", False)
        or (
            mode == "manual"
            and reset_verified
            and state_summary.fallback_count > 0
        )
    )
    required_intervals = int(
        getattr(
            provider,
            "required_intervals",
            5 if mode == "mock" else 1,
        )
    )
    multiple = (
        int(getattr(provider, "intervals_completed", 0))
        >= required_intervals
    )
    summary = {
        "success": (
            exit_code == 0
            and provider.complete
            and not state_summary.callback_errors
            and error_summary.severe_count == 0
            and error_summary.fatal_count == 0
            and control_injection
            and reset_verified
            and (fallback_verified if mode == "mock" else True)
            and (multiple if mode in {"mock", "phase7_llm"} else True)
        ),
        "mode": mode,
        "classification": classification,
        "EnergyPlus_exit_code": exit_code,
        "EnergyPlus_API_version": availability.API_version,
        "EnergyPlus_version": availability.EnergyPlus_version,
        "selected_actuator": asdict(actuator) | {
            "identifier": actuator.identifier
        },
        "control_injection_verified": control_injection,
        "observed_setpoint_change": observed_change,
        "actuator_reset_verified": reset_verified,
        "multiple_intervals_completed": multiple,
        "intervals_completed": int(
            getattr(provider, "intervals_completed", state_summary.decisions)
        ),
        "fallback_verified": fallback_verified,
        "real_llm_used": real_llm_used,
        "warning_count": error_summary.warning_count,
        "severe_count": error_summary.severe_count,
        "fatal_count": error_summary.fatal_count,
        "callback_errors": state_summary.callback_errors,
        "actuator_write_count": state_summary.applications,
        "fallback_count": state_summary.fallback_count,
        "safety_supervisor_enabled": True,
        "deterministic_safety_authority": True,
        "safety_decision_count": state_summary.safety_decision_count,
        "post_action_verification_count": (
            state_summary.post_action_verification_count
        ),
        "rollback_count": state_summary.rollback_count,
        "emergency_fallback_count": state_summary.emergency_count,
        "baseline_setpoint_c": getattr(
            provider, "baseline_setpoint_c", state_summary.baseline_setpoint_c
        ),
        "requested_setpoint_c": getattr(
            provider, "changed_setpoint_c",
            settings.manual_test_value_c if mode == "manual" else None,
        ),
        "approved_setpoint_c": state_summary.during_override_setpoint_c,
        "applied_setpoint_c": state_summary.during_override_setpoint_c,
        "observed_setpoint_c": state_summary.last_observed_setpoint_c,
        "setpoint_before_override_c": getattr(
            provider, "baseline_setpoint_c", state_summary.baseline_setpoint_c
        ),
        "setpoint_during_override_c": state_summary.during_override_setpoint_c,
        "setpoint_after_reset_c": state_summary.after_reset_setpoint_c,
        "final_optimization_result": False,
        "savings_result": False,
    }
    if mode == "phase7_llm":
        summary.update(
            {
                "llm_called": bool(
                    getattr(provider, "llm_called", False)
                ),
                "llm_completed": bool(
                    getattr(provider, "llm_completed", False)
                ),
                "llm_action_used": bool(
                    getattr(provider, "llm_action_used", False)
                ),
                "fallback_used": bool(
                    getattr(provider, "fallback_used", False)
                ),
                "proposal_source": (
                    "deterministic_runtime_fallback"
                    if getattr(provider, "fallback_used", False)
                    else "llm_runtime_decision"
                ),
                "llm_error_code": getattr(
                    provider, "llm_error_code", None
                ),
                "llm_error_message": getattr(
                    provider, "llm_error_message", None
                ),
                "raw_llm_requested_setpoint_c": getattr(
                    provider, "raw_llm_requested_setpoint_c", None
                ),
                "normalized_requested_setpoint_c": getattr(
                    provider, "normalized_requested_setpoint_c", None
                ),
                "normalization_applied": bool(
                    getattr(provider, "normalization_applied", False)
                ),
                "normalization_reason": getattr(
                    provider, "normalization_reason", None
                ),
                "fallback_reason": getattr(
                    provider, "fallback_reason", None
                ),
                "fallback_action_setpoint_c": getattr(
                    provider, "fallback_target_c", None
                ),
            }
        )
    summary["success"] = bool(summary["success"])
    safety_directory = safety_artifacts.finalize(
        safety_artifacts.build_summary(
            severe_count=error_summary.severe_count,
            fatal_count=error_summary.fatal_count,
        )
    )
    summary["phase9_safety_artifact_directory"] = str(safety_directory)
    directory = artifacts.finalize(summary)
    return Phase8RunResult(
        success=summary["success"],
        exit_code=exit_code,
        mode=mode,
        classification=classification,
        artifact_directory=directory,
        summary=summary,
    )


__all__ = ["Phase8RunResult", "run_phase8_runtime"]
