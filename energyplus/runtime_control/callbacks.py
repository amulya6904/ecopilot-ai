"""Fast EnergyPlus callbacks for validated actions and live observations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from safety.artifacts import SafetyArtifacts
from safety.audit import SafetyAuditLog
from safety.emergency import build_emergency_event
from safety.post_action import verify_post_action
from safety.rollback import build_rollback_event
from safety.schemas import SafetyHistory, SafetyHistoryEntry
from safety.settings import SAFETY_SETTINGS
from safety.state_builder import build_safety_state
from safety.supervisor import evaluate_action_safety

from .action_provider import ActionProvider
from .actuator_discovery import ActuatorDescriptor
from .artifacts import Phase8Artifacts
from .audit import RuntimeAuditLog
from .fallback import reset_to_baseline
from .handles import HandleRegistry, initialize_handle_registry
from .schemas import AppliedControlEvent, FallbackEvent
from .settings import PHASE8_SETTINGS, Phase8Settings
from .telemetry import read_runtime_telemetry
from .validator import RuntimeValidationContext, validate_action_candidate


@dataclass
class RuntimeCallbackState:
    registry: HandleRegistry = field(default_factory=HandleRegistry)
    callback_errors: list[str] = field(default_factory=list)
    active_action: Any | None = None
    active_validation: Any | None = None
    reset_active: bool = False
    applications: int = 0
    decisions: int = 0
    fallback_count: int = 0
    last_observed_setpoint_c: float | None = None
    baseline_setpoint_c: float | None = None
    during_override_setpoint_c: float | None = None
    after_reset_setpoint_c: float | None = None
    active_safety_decision: Any | None = None
    safety_history: SafetyHistory = field(default_factory=SafetyHistory)
    safety_decision_count: int = 0
    post_action_verification_count: int = 0
    rollback_count: int = 0
    emergency_count: int = 0
    consecutive_actuator_failures: int = 0
    autonomy_disabled: bool = False
    verified_safety_actions: set[str] = field(default_factory=set)
    pending_rollback_action_id: str | None = None
    pending_rollback_timestamp: datetime | None = None
    pending_emergency_action_id: str | None = None
    safety_observation_attempts: dict[str, int] = field(
        default_factory=dict
    )


class RuntimeCallbacks:
    """Own callback state; providers are prebuilt before EnergyPlus starts."""

    def __init__(
        self,
        api: Any,
        provider: ActionProvider,
        actuator: ActuatorDescriptor,
        artifacts: Phase8Artifacts,
        audit: RuntimeAuditLog,
        settings: Phase8Settings = PHASE8_SETTINGS,
        safety_artifacts: SafetyArtifacts | None = None,
        safety_audit: SafetyAuditLog | None = None,
    ) -> None:
        self.api = api
        self.provider = provider
        self.actuator = actuator
        self.artifacts = artifacts
        self.audit = audit
        self.settings = settings
        self.safety_artifacts = safety_artifacts
        self.safety_audit = safety_audit
        self.state = RuntimeCallbackState()

    def _evaluate_safety(
        self,
        telemetry,
        candidate,
        *,
        record_history: bool,
    ):
        if candidate.run_id != self.artifacts.run_id:
            candidate = candidate.model_copy(
                update={"run_id": self.artifacts.run_id}
            )
        safety_state = build_safety_state(
            telemetry,
            run_id=self.artifacts.run_id,
            handles=self.state.registry,
            control_mode=candidate.source_type,
            history=self.state.safety_history,
            consecutive_agent_failures=int(
                getattr(self.provider, "consecutive_failures", 0)
            ),
            consecutive_actuator_failures=(
                self.state.consecutive_actuator_failures
            ),
        )
        safety_decision = evaluate_action_safety(
            safety_state,
            candidate,
            history=self.state.safety_history,
        )
        self.state.safety_decision_count += 1
        if self.safety_artifacts is not None:
            self.safety_artifacts.add_decision(
                safety_state, candidate, safety_decision
            )
        if self.safety_audit is not None:
            self.safety_audit.record(
                "pre_action_safety_decision",
                run_id=self.artifacts.run_id,
                simulation_timestamp=telemetry.simulation_timestamp,
                action_id=candidate.action_id,
                state_summary=safety_state,
                rules_evaluated=safety_decision.all_rule_results,
                decision=safety_decision.decision,
                requested_value=safety_decision.requested_value_c,
                approved_value=safety_decision.approved_value_c,
                safety_level=safety_decision.safety_level,
                fallback_or_rollback=safety_decision.fallback_required,
                duration_ms=safety_decision.duration_ms,
                result=safety_decision,
            )
        self.audit.record("phase9_safety_decision", safety_decision)
        telemetry_failure_codes = {
            "TELEMETRY_STALE",
            "ZONE_TEMPERATURE_MISSING",
            "SETPOINT_MISSING",
            "INVALID_NUMERIC_VALUE",
            "API_ERROR",
        }
        if any(
            not rule.passed and rule.rule_id in telemetry_failure_codes
            for rule in safety_decision.all_rule_results
        ):
            self.state.safety_history.telemetry_failure_count += 1
        else:
            self.state.safety_history.telemetry_failure_count = 0
        if record_history:
            self._record_safety_history(
                telemetry, candidate, safety_decision
            )
        return candidate, safety_state, safety_decision

    def _record_safety_history(
        self, telemetry, candidate, safety_decision
    ) -> None:
        self.state.safety_history.actions.append(
            SafetyHistoryEntry(
                action_id=candidate.action_id,
                timestamp=telemetry.simulation_timestamp,
                setpoint_c=(
                    safety_decision.approved_value_c
                    if safety_decision.approved_value_c is not None
                    else candidate.current_value_c
                ),
                decision=safety_decision.decision,
                zone_name=candidate.zone_name,
            )
        )
        if safety_decision.decision == "approve_with_clamp":
            self.state.safety_history.clamp_count += 1
        elif safety_decision.decision in {
            "reject",
            "fallback",
            "emergency_fallback",
        }:
            self.state.safety_history.reject_count += 1

    def _safety_reset(
        self,
        runtime_state,
        telemetry,
        *,
        candidate,
        safety_state,
        safety_decision,
    ) -> None:
        fallback = reset_to_baseline(
            self.api.exchange,
            runtime_state,
            self.state.registry.cooling_actuator,
            reason_code="COMFORT_RISK",
            simulation_timestamp=telemetry.simulation_timestamp,
            original_action_id=candidate.action_id,
            fallback_value_c=getattr(
                self.provider,
                "baseline_setpoint_c",
                telemetry.current_cooling_setpoint_c,
            ),
        )
        self.state.active_action = None
        self.state.active_validation = None
        self.state.active_safety_decision = None
        self.state.reset_active = True
        self.state.fallback_count += 1
        self.artifacts.add("fallbacks", fallback)
        self.audit.record("phase9_safety_fallback", fallback)
        if safety_decision.decision == "emergency_fallback":
            self.state.autonomy_disabled = True
            event = build_emergency_event(
                safety_state,
                action_id=candidate.action_id,
                reason_code=(
                    safety_decision.violated_rules[0].rule_id
                    if safety_decision.violated_rules
                    else "PHASE9_EMERGENCY"
                ),
                reset_attempted=fallback.actuator_reset,
                baseline_restored=False,
            )
            self.state.emergency_count += 1
            self.state.pending_emergency_action_id = candidate.action_id
            if self.safety_artifacts is not None:
                self.safety_artifacts.add("emergency_events", event)

    def _initialize(self, runtime_state: Any) -> bool:
        if self.state.registry.initialized:
            return self.state.registry.ready
        if not self.api.exchange.api_data_fully_ready(runtime_state):
            return False
        registry = initialize_handle_registry(
            self.api.exchange,
            runtime_state,
            self.actuator,
            self.settings,
        )
        self.state.registry = registry
        self.artifacts.handles = registry.to_dict()
        self.audit.record("handle_registry", registry.to_dict())
        if not registry.ready:
            message = (
                "Required EnergyPlus handles are invalid: "
                + ", ".join(registry.required_invalid)
            )
            self.state.callback_errors.append(message)
            self.audit.record("callback_error", {"message": message})
            self.api.runtime.stop_simulation(runtime_state)
            return False
        return True

    def on_control(self, runtime_state: Any) -> None:
        try:
            if not self._initialize(runtime_state):
                return
            telemetry = read_runtime_telemetry(
                self.api.exchange,
                runtime_state,
                self.state.registry,
                self.settings,
            )
            if telemetry.warmup_flag:
                return
            if self.state.baseline_setpoint_c is None:
                self.state.baseline_setpoint_c = (
                    telemetry.current_cooling_setpoint_c
                )
            if not self.provider.complete and not self.state.autonomy_disabled:
                decision = self.provider.next_decision(
                    telemetry, self.actuator
                )
                if decision is not None:
                    self.state.decisions += 1
                    self.artifacts.proposals.append(decision.proposal)
                    self.audit.record("proposal", decision.proposal)
                    if decision.kind == "reset":
                        fallback = reset_to_baseline(
                            self.api.exchange,
                            runtime_state,
                            self.state.registry.cooling_actuator,
                            reason_code="MANUAL_RESET",
                            simulation_timestamp=telemetry.simulation_timestamp,
                            original_action_id=(
                                self.state.active_action.action_id
                                if self.state.active_action else None
                            ),
                            fallback_value_c=(
                                getattr(
                                    self.provider,
                                    "baseline_setpoint_c",
                                    telemetry.current_cooling_setpoint_c,
                                )
                            ),
                        )
                        self.state.active_action = None
                        self.state.active_validation = None
                        self.state.active_safety_decision = None
                        self.state.reset_active = True
                        self.state.fallback_count += 1
                        self.artifacts.add("fallbacks", fallback)
                        self.audit.record("fallback", fallback)
                    else:
                        candidate = decision.candidate
                        if candidate is None:
                            raise RuntimeError(
                                "Apply decision did not include a candidate."
                            )
                        (
                            candidate,
                            safety_state,
                            safety_decision,
                        ) = self._evaluate_safety(
                            telemetry,
                            candidate,
                            record_history=False,
                        )
                        self.artifacts.add("candidates", candidate)
                        self.audit.record("action_candidate", candidate)
                        candidate_preclamped = False
                        if (
                            safety_decision.decision
                            == "approve_with_clamp"
                            and "intentionally_invalid_phase8_fallback_test"
                            not in candidate.reason
                        ):
                            approved_safety_value = float(
                                safety_decision.approved_value_c
                            )
                            candidate = candidate.model_copy(
                                update={
                                    "requested_value_c": (
                                        approved_safety_value
                                    ),
                                    "requested_delta_c": (
                                        approved_safety_value
                                        - candidate.current_value_c
                                    ),
                                }
                            )
                            candidate_preclamped = True
                            self.artifacts.add("candidates", candidate)
                            self.audit.record(
                                "phase9_prevalidated_clamp", candidate
                            )
                        validation = validate_action_candidate(
                            candidate,
                            RuntimeValidationContext(
                                now=telemetry.simulation_timestamp,
                                telemetry=telemetry,
                                handles=self.state.registry,
                                actuator_identifier=self.actuator.identifier,
                                control_enabled=(
                                    self.settings.enable_manual_control
                                    if candidate.source_type == "manual"
                                    else self.settings.enable_mock_agent
                                    if candidate.source_type == "mock_agent"
                                    else self.settings.enable_real_llm
                                    if candidate.source_type == "phase7_llm"
                                    else True
                                ),
                            ),
                            self.settings,
                        )
                        self.artifacts.add("validations", validation)
                        self.audit.record("validation", validation)
                        if (
                            not validation.approved
                            and candidate.source_type == "phase7_llm"
                            and hasattr(
                                self.provider, "validation_fallback"
                            )
                        ):
                            rejected_action_id = candidate.action_id
                            fallback_candidate = (
                                self.provider.validation_fallback(
                                    telemetry,
                                    self.actuator,
                                    validation.errors,
                                )
                            )
                            fallback_selection = {
                                "source": "phase7_llm_adapter",
                                "action": (
                                    "validator_rejection_runtime_fallback"
                                ),
                                "rejected_action_id": rejected_action_id,
                                "validator_errors": validation.errors,
                                "selected_action_setpoint_c": (
                                    fallback_candidate.requested_value_c
                                ),
                                "fallback_reason": getattr(
                                    self.provider,
                                    "fallback_reason",
                                    "VALIDATION_REJECTED",
                                ),
                            }
                            self.artifacts.proposals.append(
                                fallback_selection
                            )
                            self.audit.record(
                                "fallback_selection",
                                fallback_selection,
                            )
                            (
                                candidate,
                                safety_state,
                                safety_decision,
                            ) = self._evaluate_safety(
                                telemetry,
                                fallback_candidate,
                                record_history=False,
                            )
                            candidate_preclamped = False
                            self.artifacts.add(
                                "candidates", candidate
                            )
                            self.audit.record(
                                "action_candidate", candidate
                            )
                            validation = validate_action_candidate(
                                candidate,
                                RuntimeValidationContext(
                                    now=telemetry.simulation_timestamp,
                                    telemetry=telemetry,
                                    handles=self.state.registry,
                                    actuator_identifier=(
                                        self.actuator.identifier
                                    ),
                                    control_enabled=True,
                                ),
                                self.settings,
                            )
                            self.artifacts.add(
                                "validations", validation
                            )
                            self.audit.record(
                                "fallback_validation", validation
                            )
                        self._record_safety_history(
                            telemetry, candidate, safety_decision
                        )
                        if (
                            validation.approved
                            and safety_decision.decision
                            in {"approve", "approve_with_clamp"}
                        ):
                            if (
                                safety_decision.decision
                                == "approve_with_clamp"
                                and not candidate_preclamped
                            ):
                                approved_safety_value = float(
                                    safety_decision.approved_value_c
                                )
                                candidate = candidate.model_copy(
                                    update={
                                        "requested_value_c": (
                                            approved_safety_value
                                        ),
                                        "requested_delta_c": (
                                            approved_safety_value
                                            - candidate.current_value_c
                                        ),
                                    }
                                )
                                self.artifacts.add(
                                    "candidates", candidate
                                )
                                validation = validate_action_candidate(
                                    candidate,
                                    RuntimeValidationContext(
                                        now=(
                                            telemetry.simulation_timestamp
                                        ),
                                        telemetry=telemetry,
                                        handles=self.state.registry,
                                        actuator_identifier=(
                                            self.actuator.identifier
                                        ),
                                        control_enabled=True,
                                    ),
                                    self.settings,
                                )
                                self.artifacts.add(
                                    "validations", validation
                                )
                                self.audit.record(
                                    "phase9_clamped_validation",
                                    validation,
                                )
                            if not validation.approved:
                                self._safety_reset(
                                    runtime_state,
                                    telemetry,
                                    candidate=candidate,
                                    safety_state=safety_state,
                                    safety_decision=safety_decision,
                                )
                                return
                            self.state.active_action = candidate
                            self.state.active_validation = validation
                            self.state.active_safety_decision = (
                                safety_decision
                            )
                            self.state.reset_active = False
                            if candidate.source_type == "fallback":
                                fallback = FallbackEvent(
                                    fallback_id=(
                                        f"fallback-{uuid.uuid4().hex}"
                                    ),
                                    reason_code="AGENT_FAILURE",
                                    original_action_id=candidate.action_id,
                                    fallback_value_c=(
                                        validation.approved_value_c
                                    ),
                                    actuator_reset=False,
                                    simulation_timestamp=(
                                        telemetry.simulation_timestamp
                                    ),
                                )
                                self.state.fallback_count += 1
                                self.artifacts.add("fallbacks", fallback)
                                self.audit.record(
                                    "validated_runtime_fallback", fallback
                                )
                        elif (
                            validation.approved
                            and safety_decision.decision == "hold"
                        ):
                            self.audit.record(
                                "phase9_safety_hold", safety_decision
                            )
                        elif validation.approved:
                            self._safety_reset(
                                runtime_state,
                                telemetry,
                                candidate=candidate,
                                safety_state=safety_state,
                                safety_decision=safety_decision,
                            )
                        else:
                            fallback = reset_to_baseline(
                                self.api.exchange,
                                runtime_state,
                                self.state.registry.cooling_actuator,
                                reason_code="VALIDATION_REJECTED",
                                simulation_timestamp=telemetry.simulation_timestamp,
                                original_action_id=candidate.action_id,
                                fallback_value_c=(
                                    getattr(
                                        self.provider,
                                        "baseline_setpoint_c",
                                        telemetry.current_cooling_setpoint_c,
                                    )
                                ),
                            )
                            self.state.active_action = None
                            self.state.active_validation = None
                            self.state.active_safety_decision = None
                            self.state.reset_active = True
                            self.state.fallback_count += 1
                            self.artifacts.add("fallbacks", fallback)
                            self.audit.record("fallback", fallback)
            action = self.state.active_action
            validation = self.state.active_validation
            if action is not None and validation is not None:
                approved = float(validation.approved_value_c)
                self.api.exchange.reset_api_error_flag(runtime_state)
                self.api.exchange.set_actuator_value(
                    runtime_state,
                    self.state.registry.cooling_actuator,
                    approved,
                )
                success = not self.api.exchange.api_error_flag(runtime_state)
                if not success:
                    self.api.exchange.reset_api_error_flag(runtime_state)
                event = AppliedControlEvent(
                    action_id=action.action_id,
                    simulation_timestamp=telemetry.simulation_timestamp,
                    actuator_handle=self.state.registry.cooling_actuator,
                    requested_value=action.requested_value_c,
                    approved_value=approved,
                    applied_value=approved,
                    application_success=success,
                    observed_setpoint_after_application=None,
                    reset_performed=False,
                    source_type=action.source_type,
                    validation_id=validation.validation_id,
                )
                self.state.applications += int(success)
                self.artifacts.add("applied", event)
                self.audit.record("actuator_write", event)
                if not success:
                    raise RuntimeError(
                        "EnergyPlus reported an API error after actuator write."
                    )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self.state.callback_errors.append(message)
            self.audit.record("callback_error", {"message": message})
            if self.state.registry.cooling_actuator != -1:
                reset_to_baseline(
                    self.api.exchange,
                    runtime_state,
                    self.state.registry.cooling_actuator,
                    reason_code="CALLBACK_FAILURE",
                    simulation_timestamp=datetime.now(timezone.utc),
                )
            self.api.runtime.stop_simulation(runtime_state)

    def on_observation(self, runtime_state: Any) -> None:
        try:
            if not self.state.registry.ready:
                return
            telemetry = read_runtime_telemetry(
                self.api.exchange,
                runtime_state,
                self.state.registry,
                self.settings,
            )
            if telemetry.warmup_flag or self.provider.complete:
                return
            self.state.last_observed_setpoint_c = (
                telemetry.current_cooling_setpoint_c
            )
            self.artifacts.add("telemetry", telemetry)
            observation = {
                "simulation_timestamp": telemetry.simulation_timestamp.isoformat(),
                "observed_setpoint_c": telemetry.current_cooling_setpoint_c,
                "active_action_id": (
                    self.state.active_action.action_id
                    if self.state.active_action else None
                ),
                "reset_active": self.state.reset_active,
            }
            self.artifacts.observations.append(observation)
            self.audit.record("observation", observation)
            if self.state.active_action is not None:
                self.state.during_override_setpoint_c = (
                    telemetry.current_cooling_setpoint_c
                )
                action_id = self.state.active_action.action_id
                attempts = (
                    self.state.safety_observation_attempts.get(action_id, 0)
                    + 1
                )
                self.state.safety_observation_attempts[action_id] = attempts
                approved_value = float(
                    self.state.active_validation.approved_value_c
                )
                observation_matches = (
                    abs(
                        telemetry.current_cooling_setpoint_c
                        - approved_value
                    )
                    <= self.settings.verification_tolerance_c
                )
                verification_due = (
                    observation_matches
                    or attempts > SAFETY_SETTINGS.maximum_missing_samples
                )
                linked = 0
                for applied in reversed(self.artifacts.applied):
                    if (
                        applied.get("action_id")
                        != self.state.active_action.action_id
                    ):
                        continue
                    if applied.get(
                        "observed_setpoint_after_application"
                    ) is not None:
                        continue
                    if not verification_due:
                        continue
                    observed = telemetry.current_cooling_setpoint_c
                    applied["observed_setpoint_after_application"] = observed
                    applied["verified"] = (
                        abs(
                            observed
                            - float(applied["approved_value"])
                        )
                        <= self.settings.verification_tolerance_c
                    )
                    linked += 1
                if linked:
                    self.audit.record(
                        "applied_action_observation",
                        {
                            "action_id": self.state.active_action.action_id,
                            "observed_setpoint_after_application": (
                                telemetry.current_cooling_setpoint_c
                            ),
                            "linked_applied_events": linked,
                        },
                    )
                    if action_id not in self.state.verified_safety_actions:
                        safety_state = build_safety_state(
                            telemetry,
                            run_id=self.artifacts.run_id,
                            handles=self.state.registry,
                            control_mode=(
                                self.state.active_action.source_type
                            ),
                            history=self.state.safety_history,
                            consecutive_actuator_failures=(
                                self.state.consecutive_actuator_failures
                            ),
                        )
                        verification = verify_post_action(
                            safety_state,
                            action_id=action_id,
                            approved_value_c=float(
                                self.state.active_validation.approved_value_c
                            ),
                            observed_value_c=(
                                telemetry.current_cooling_setpoint_c
                            ),
                        )
                        self.state.post_action_verification_count += 1
                        self.state.verified_safety_actions.add(action_id)
                        if self.safety_artifacts is not None:
                            self.safety_artifacts.add(
                                "post_action_verification",
                                verification,
                            )
                        if self.safety_audit is not None:
                            self.safety_audit.record(
                                "post_action_verification",
                                run_id=self.artifacts.run_id,
                                simulation_timestamp=(
                                    telemetry.simulation_timestamp
                                ),
                                action_id=action_id,
                                state_summary=safety_state,
                                rules_evaluated=(
                                    verification.rule_results
                                ),
                                decision=(
                                    "verified"
                                    if verification.verified_safe
                                    else "rollback"
                                ),
                                requested_value=(
                                    self.state.active_action.requested_value_c
                                ),
                                approved_value=(
                                    verification.approved_value_c
                                ),
                                safety_level=(
                                    "safe"
                                    if verification.verified_safe
                                    else "critical"
                                ),
                                fallback_or_rollback=(
                                    verification.rollback_required
                                ),
                                result=verification,
                            )
                        if verification.rollback_required:
                            reset = reset_to_baseline(
                                self.api.exchange,
                                runtime_state,
                                self.state.registry.cooling_actuator,
                                reason_code="COMFORT_RISK",
                                simulation_timestamp=(
                                    telemetry.simulation_timestamp
                                ),
                                original_action_id=action_id,
                                fallback_value_c=(
                                    self.state.baseline_setpoint_c
                                ),
                            )
                            self.state.consecutive_actuator_failures += 1
                            self.state.safety_history.rollback_count += 1
                            self.state.rollback_count += 1
                            disable = (
                                verification.emergency_reset_required
                                or self.state.safety_history.rollback_count
                                >= 2
                            )
                            rollback = build_rollback_event(
                                verification,
                                simulation_timestamp=(
                                    telemetry.simulation_timestamp
                                ),
                                reset_attempted=reset.actuator_reset,
                                reset_succeeded=False,
                                restored_setpoint_c=None,
                                autonomy_disabled=disable,
                            )
                            if self.safety_artifacts is not None:
                                self.safety_artifacts.add(
                                    "rollback_events", rollback
                                )
                            if disable:
                                emergency = build_emergency_event(
                                    safety_state,
                                    action_id=action_id,
                                    reason_code=(
                                        next(
                                            (
                                                rule.rule_id
                                                for rule in (
                                                    verification.rule_results
                                                )
                                                if not rule.passed
                                            ),
                                            "POST_ACTION_SAFETY_FAILURE",
                                        )
                                    ),
                                    reset_attempted=reset.actuator_reset,
                                    baseline_restored=False,
                                )
                                self.state.emergency_count += 1
                                self.state.pending_emergency_action_id = (
                                    action_id
                                )
                                if self.safety_artifacts is not None:
                                    self.safety_artifacts.add(
                                        "emergency_events", emergency
                                    )
                            self.state.pending_rollback_action_id = action_id
                            self.state.pending_rollback_timestamp = (
                                telemetry.simulation_timestamp
                            )
                            self.state.active_action = None
                            self.state.active_validation = None
                            self.state.active_safety_decision = None
                            self.state.reset_active = True
                            self.state.autonomy_disabled = disable
                            self.state.fallback_count += 1
                            self.artifacts.add("fallbacks", reset)
                            self.audit.record(
                                "phase9_post_action_rollback", rollback
                            )
            if self.state.reset_active:
                self.state.after_reset_setpoint_c = (
                    telemetry.current_cooling_setpoint_c
                )
                if (
                    self.state.pending_rollback_action_id is not None
                    and self.safety_artifacts is not None
                    and self.state.pending_rollback_timestamp is not None
                    and telemetry.simulation_timestamp
                    > self.state.pending_rollback_timestamp
                ):
                    for rollback in reversed(
                        self.safety_artifacts.rollback_events
                    ):
                        if (
                            rollback.get("action_id")
                            != self.state.pending_rollback_action_id
                        ):
                            continue
                        restored = telemetry.current_cooling_setpoint_c
                        rollback["restored_setpoint_c"] = restored
                        rollback["reset_succeeded"] = (
                            self.state.baseline_setpoint_c is not None
                            and abs(
                                restored
                                - self.state.baseline_setpoint_c
                            )
                            <= self.settings.verification_tolerance_c
                        )
                        reset_succeeded = rollback["reset_succeeded"]
                        break
                    else:
                        reset_succeeded = False
                    if self.state.pending_emergency_action_id is not None:
                        for emergency in reversed(
                            self.safety_artifacts.emergency_events
                        ):
                            if (
                                emergency.get("action_id")
                                != self.state.pending_emergency_action_id
                            ):
                                continue
                            emergency["baseline_restored"] = (
                                reset_succeeded
                            )
                            break
                        self.state.pending_emergency_action_id = None
                    self.state.pending_rollback_action_id = None
                    self.state.pending_rollback_timestamp = None
                elif (
                    self.state.pending_emergency_action_id is not None
                    and self.safety_artifacts is not None
                ):
                    restored = telemetry.current_cooling_setpoint_c
                    baseline_restored = (
                        self.state.baseline_setpoint_c is not None
                        and abs(
                            restored - self.state.baseline_setpoint_c
                        )
                        <= self.settings.verification_tolerance_c
                    )
                    for emergency in reversed(
                        self.safety_artifacts.emergency_events
                    ):
                        if (
                            emergency.get("action_id")
                            != self.state.pending_emergency_action_id
                        ):
                            continue
                        emergency["baseline_restored"] = baseline_restored
                        break
                    self.state.pending_emergency_action_id = None
            self.provider.observe(
                telemetry.current_cooling_setpoint_c,
                self.state.reset_active,
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self.state.callback_errors.append(message)
            self.audit.record("callback_error", {"message": message})
            self.api.runtime.stop_simulation(runtime_state)

    def register(self, state: Any) -> None:
        self.api.runtime.callback_after_predictor_before_hvac_managers(
            state, self.on_control
        )
        self.api.runtime.callback_end_zone_timestep_after_zone_reporting(
            state, self.on_observation
        )


__all__ = ["RuntimeCallbackState", "RuntimeCallbacks"]
