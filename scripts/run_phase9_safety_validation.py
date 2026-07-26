"""Complete offline and real-runtime Phase 9 safety validation."""

import csv
from datetime import timedelta
import json
from typing import Any

from energyplus.runtime_control.action_provider import (
    ProviderDecision,
    build_candidate,
)
from energyplus.runtime_control.api_loader import (
    inspect_runtime_availability,
)
from energyplus.runtime_control.orchestrator import run_manual_validation
from energyplus.runtime_control.runtime_runner import run_phase8_runtime
from safety.artifacts import SafetyArtifacts
from safety.audit import SafetyAuditLog
from safety.emergency import build_emergency_event
from safety.fault_injection import (
    NOW,
    make_candidate,
    make_state,
    run_fault_injection_suite,
)
from safety.post_action import verify_post_action
from safety.rollback import build_rollback_event
from safety.schemas import SafetyHistory
from safety.supervisor import evaluate_action_safety


class Phase9ClampedActionProvider:
    """Request an unsafe value and observe the supervised nearby-safe clamp."""

    def __init__(self) -> None:
        self.complete = False
        self._stage = 0
        self._decision_hour = None
        self.baseline_setpoint_c: float | None = None
        self.changed_setpoint_c: float | None = None
        self.override_observed = False
        self.reset_observed = False

    @property
    def intervals_completed(self) -> int:
        return self._stage

    def next_decision(self, telemetry, actuator):
        hour_key = (
            telemetry.simulation_timestamp.timetuple().tm_yday,
            telemetry.simulation_timestamp.hour,
        )
        if hour_key == self._decision_hour:
            return None
        if self._stage == 0:
            if telemetry.current_cooling_setpoint_c > 23.0:
                return None
            self._decision_hour = hour_key
            self._stage = 1
            self.baseline_setpoint_c = (
                telemetry.current_cooling_setpoint_c
            )
            self.changed_setpoint_c = min(
                self.baseline_setpoint_c + 1.0, 28.0
            )
            candidate = build_candidate(
                telemetry,
                actuator,
                29.0,
                "mock_agent",
                objective="reduce_energy",
                reason="phase9_clamp_validation",
            )
            return ProviderDecision(
                "apply",
                candidate,
                {
                    "source": "phase9_validation",
                    "requested_setpoint_c": 29.0,
                    "expected_clamped_setpoint_c": (
                        self.changed_setpoint_c
                    ),
                },
                "phase9_clamped_apply",
            )
        if self._stage == 1:
            self._decision_hour = hour_key
            self._stage = 2
            return ProviderDecision(
                "reset",
                None,
                {
                    "source": "phase9_validation",
                    "action": "reset",
                },
                "phase9_clamped_reset",
            )
        return None

    def observe(self, setpoint_c: float, reset_active: bool) -> None:
        if (
            not reset_active
            and self.changed_setpoint_c is not None
            and abs(setpoint_c - self.changed_setpoint_c) <= 0.15
        ):
            self.override_observed = True
        if (
            reset_active
            and self.baseline_setpoint_c is not None
            and abs(setpoint_c - self.baseline_setpoint_c) <= 0.15
        ):
            self.reset_observed = True
            self.complete = self.override_observed


def _evaluate_offline(artifacts: SafetyArtifacts) -> list[str]:
    specifications = [
        ("approve", make_state(), make_candidate(), SafetyHistory()),
        (
            "approve_with_clamp",
            make_state(),
            make_candidate(requested=29.0),
            SafetyHistory(),
        ),
        (
            "hold",
            make_state(warmup=True),
            make_candidate(),
            SafetyHistory(),
        ),
        (
            "reject",
            make_state(),
            make_candidate(requested=21.0, objective="reduce_energy"),
            SafetyHistory(),
        ),
        (
            "fallback",
            make_state(telemetry_age_seconds=301.0),
            make_candidate(),
            SafetyHistory(),
        ),
        (
            "emergency_fallback",
            make_state(severe_runtime_error=True),
            make_candidate(),
            SafetyHistory(),
        ),
    ]
    actual: list[str] = []
    audit = SafetyAuditLog()
    for expected, state, candidate, history in specifications:
        decision = evaluate_action_safety(
            state, candidate, history=history
        )
        artifacts.add_decision(state, candidate, decision)
        actual.append(decision.decision)
        audit.record(
            "validation_scenario",
            run_id=artifacts.run_id,
            simulation_timestamp=state.simulation_timestamp,
            action_id=candidate.action_id,
            state_summary=state,
            rules_evaluated=decision.all_rule_results,
            decision=decision.decision,
            requested_value=decision.requested_value_c,
            approved_value=decision.approved_value_c,
            safety_level=decision.safety_level,
            fallback_or_rollback=decision.fallback_required,
            duration_ms=decision.duration_ms,
            result={"expected": expected, "matched": decision.decision == expected},
        )
    return actual


def _post_and_recovery(artifacts: SafetyArtifacts) -> tuple[bool, bool]:
    safe_state = make_state(cooling_setpoint_c=23.0)
    verified = verify_post_action(
        safe_state,
        action_id="phase9-post-safe",
        approved_value_c=23.0,
        observed_value_c=23.0,
    )
    artifacts.add("post_action_verification", verified)
    mismatch = verify_post_action(
        make_state(),
        action_id="phase9-rollback-test",
        approved_value_c=23.0,
        observed_value_c=22.0,
    )
    artifacts.add("post_action_verification", mismatch)
    rollback = build_rollback_event(
        mismatch,
        simulation_timestamp=NOW,
        reset_attempted=True,
        reset_succeeded=True,
        restored_setpoint_c=22.0,
        autonomy_disabled=False,
    )
    artifacts.add("rollback_events", rollback)
    emergency_state = make_state(severe_runtime_error=True)
    emergency = build_emergency_event(
        emergency_state,
        action_id="phase9-emergency-test",
        reason_code="SEVERE_RUNTIME_ERROR",
        reset_attempted=True,
        baseline_restored=True,
    )
    artifacts.add("emergency_events", emergency)
    return (
        verified.verified_safe,
        rollback.reset_succeeded
        and emergency.autonomy_disabled
        and emergency.operator_acknowledgement_required,
    )


def _traceability_complete(directory) -> bool:
    path = directory / "applied_actions.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return bool(rows) and all(
        row.get("observed_setpoint_after_application")
        not in {None, "", "None"}
        for row in rows
    )


def run_validation(
    *,
    use_energyplus_when_available: bool = True,
) -> dict[str, Any]:
    artifacts = SafetyArtifacts("validation")
    decisions = _evaluate_offline(artifacts)
    post_ok, recovery_ok = _post_and_recovery(artifacts)
    faults = run_fault_injection_suite()
    artifacts.fault_injection_results.extend(faults)
    availability = inspect_runtime_availability()
    manual = None
    clamped = None
    runtime_expected = (
        use_energyplus_when_available and availability.available
    )
    if runtime_expected:
        manual = run_manual_validation()
        clamped = run_phase8_runtime(
            Phase9ClampedActionProvider(),
            mode="phase9-clamp",
            classification=(
                "safety_supervised_energyplus_runtime_validation"
            ),
        )
    runtime_ok = (
        True
        if not runtime_expected
        else bool(
            manual
            and clamped
            and manual.success
            and clamped.success
            and manual.summary["severe_count"] == 0
            and manual.summary["fatal_count"] == 0
            and clamped.summary["severe_count"] == 0
            and clamped.summary["fatal_count"] == 0
            and _traceability_complete(manual.artifact_directory)
            and _traceability_complete(clamped.artifact_directory)
        )
    )
    expected_decisions = {
        "approve",
        "approve_with_clamp",
        "hold",
        "reject",
        "fallback",
        "emergency_fallback",
    }
    accepted = (
        set(decisions) == expected_decisions
        and post_ok
        and recovery_ok
        and len(faults) == 22
        and all(item["passed"] for item in faults)
        and runtime_ok
        and (not availability.available or runtime_expected)
    )
    artifacts.metadata["acceptance_checks_passed"] = accepted
    artifacts.metadata["energyplus_runtime_available"] = (
        availability.available
    )
    artifacts.metadata["energyplus_runtime_executed"] = runtime_expected
    artifacts.metadata["phase8_manual_artifact_directory"] = (
        str(manual.artifact_directory) if manual else None
    )
    artifacts.metadata["phase8_clamped_artifact_directory"] = (
        str(clamped.artifact_directory) if clamped else None
    )
    severe = (
        int(manual.summary["severe_count"])
        + int(clamped.summary["severe_count"])
        if manual and clamped
        else 0
    )
    fatal = (
        int(manual.summary["fatal_count"])
        + int(clamped.summary["fatal_count"])
        if manual and clamped
        else 0
    )
    summary = artifacts.build_summary(
        severe_count=severe, fatal_count=fatal
    )
    directory = artifacts.finalize(summary)
    return {
        "success": accepted,
        "classification": summary.classification,
        "artifact_directory": str(directory),
        "fault_scenarios_passed": sum(
            bool(item["passed"]) for item in faults
        ),
        "fault_scenarios_total": len(faults),
        "decision_outcomes": decisions,
        "post_action_verified": post_ok,
        "rollback_and_emergency_verified": recovery_ok,
        "energyplus_runtime_available": availability.available,
        "energyplus_runtime_executed": runtime_expected,
        "energyplus_runtime_verified": runtime_ok,
        "phase8_manual_artifact_directory": (
            str(manual.artifact_directory) if manual else None
        ),
        "phase8_clamped_artifact_directory": (
            str(clamped.artifact_directory) if clamped else None
        ),
        "severe_count": severe,
        "fatal_count": fatal,
        "final_optimization_result": False,
        "savings_result": False,
    }


def main() -> int:
    result = run_validation()
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
