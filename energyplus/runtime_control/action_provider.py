"""Precomputed/manual action providers; no model inference runs in callbacks."""

from dataclasses import dataclass
from datetime import timedelta
import math
from typing import Any, Literal, Protocol
import uuid

from .actuator_discovery import ActuatorDescriptor
from .schemas import ExecutableActionCandidate, RuntimeTelemetrySnapshot
from .settings import PHASE8_SETTINGS, Phase8Settings


@dataclass(frozen=True)
class ProviderDecision:
    kind: Literal["apply", "reset"]
    candidate: ExecutableActionCandidate | None
    proposal: dict[str, Any]
    label: str
    fallback_reason: str | None = None


class ActionProvider(Protocol):
    complete: bool

    def next_decision(
        self,
        telemetry: RuntimeTelemetrySnapshot,
        actuator: ActuatorDescriptor,
    ) -> ProviderDecision | None: ...

    def observe(self, setpoint_c: float, reset_active: bool) -> None: ...


def build_candidate(
    telemetry: RuntimeTelemetrySnapshot,
    actuator: ActuatorDescriptor,
    requested_value_c: float,
    source_type: Literal[
        "manual",
        "mock_agent",
        "phase7_llm",
        "fallback",
        "reproducible_policy",
    ],
    *,
    proposal_id: str | None = None,
    phase7_validated: bool | None = None,
    confidence: float | None = None,
    run_id: str | None = None,
    objective: Literal[
        "reduce_energy",
        "reduce_peak_demand",
        "maintain_comfort",
    ] = "maintain_comfort",
    control_type: Literal["cooling_setpoint"] = "cooling_setpoint",
    reason: str = "",
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> ExecutableActionCandidate:
    now = telemetry.simulation_timestamp
    return ExecutableActionCandidate(
        action_id=f"action-{uuid.uuid4().hex}",
        source_proposal_id=proposal_id,
        source_type=source_type,
        zone_name=settings.controlled_zone,
        actuator_identifier=actuator.identifier,
        current_value_c=telemetry.current_cooling_setpoint_c,
        requested_value_c=requested_value_c,
        requested_delta_c=(
            requested_value_c - telemetry.current_cooling_setpoint_c
        ),
        effective_from=now,
        effective_until=now + timedelta(
            minutes=settings.decision_interval_minutes
        ),
        evidence_references=["EnergyPlusRuntime:live_telemetry"],
        created_at=now,
        expires_at=now + timedelta(
            minutes=settings.action_stale_after_minutes
        ),
        phase7_validated=phase7_validated,
        confidence=confidence,
        run_id=run_id,
        objective=objective,
        control_type=control_type,
        reason=reason,
    )


class ManualActionProvider:
    """Apply 23 C for one hour after the occupied schedule becomes active."""

    def __init__(
        self, settings: Phase8Settings = PHASE8_SETTINGS
    ) -> None:
        self.settings = settings
        self.complete = False
        self._stage = 0
        self._decision_hour: tuple[int, int] | None = None
        self.baseline_setpoint_c: float | None = None
        self.override_observed = False
        self.reset_observed = False

    def next_decision(
        self,
        telemetry: RuntimeTelemetrySnapshot,
        actuator: ActuatorDescriptor,
    ) -> ProviderDecision | None:
        stamp = telemetry.simulation_timestamp
        hour_key = (stamp.timetuple().tm_yday, stamp.hour)
        if hour_key == self._decision_hour:
            return None
        if self._stage == 0:
            delta = self.settings.manual_test_value_c - (
                telemetry.current_cooling_setpoint_c
            )
            if abs(delta) > self.settings.maximum_setpoint_change_c:
                return None
            self.baseline_setpoint_c = telemetry.current_cooling_setpoint_c
            self._decision_hour = hour_key
            self._stage = 1
            candidate = build_candidate(
                telemetry,
                actuator,
                self.settings.manual_test_value_c,
                "manual",
                settings=self.settings,
            )
            return ProviderDecision(
                "apply",
                candidate,
                {
                    "source": "manual",
                    "requested_setpoint_c": self.settings.manual_test_value_c,
                },
                "manual_23c_override",
            )
        if self._stage == 1:
            self._decision_hour = hour_key
            self._stage = 2
            return ProviderDecision(
                "reset",
                None,
                {"source": "manual", "action": "reset_actuator"},
                "manual_reset",
            )
        return None

    def observe(self, setpoint_c: float, reset_active: bool) -> None:
        if self._stage == 1 and abs(
            setpoint_c - self.settings.manual_test_value_c
        ) <= self.settings.verification_tolerance_c:
            self.override_observed = True
        if (
            self._stage >= 2
            and reset_active
            and self.baseline_setpoint_c is not None
            and abs(setpoint_c - self.baseline_setpoint_c)
            <= self.settings.verification_tolerance_c
        ):
            self.reset_observed = True
            self.complete = self.override_observed


class MockActionProvider:
    """Five deterministic hourly decisions, including a rejected fifth action."""

    def __init__(
        self, settings: Phase8Settings = PHASE8_SETTINGS
    ) -> None:
        self.settings = settings
        self.complete = False
        self._stage = 0
        self._decision_hour: tuple[int, int] | None = None
        self.baseline_setpoint_c: float | None = None
        self.changed_setpoint_c: float | None = None
        self.change_observed = False
        self.reset_observed = False
        self.fallback_observed = False

    @property
    def intervals_completed(self) -> int:
        return self._stage

    def next_decision(
        self,
        telemetry: RuntimeTelemetrySnapshot,
        actuator: ActuatorDescriptor,
    ) -> ProviderDecision | None:
        stamp = telemetry.simulation_timestamp
        hour_key = (stamp.timetuple().tm_yday, stamp.hour)
        if hour_key == self._decision_hour:
            return None
        if self._stage == 0:
            if telemetry.current_cooling_setpoint_c > 23.0:
                return None
            self.baseline_setpoint_c = telemetry.current_cooling_setpoint_c
        if self._stage >= 5:
            return None
        self._decision_hour = hour_key
        stage = self._stage
        self._stage += 1
        if stage == 3:
            return ProviderDecision(
                "reset",
                None,
                {"source": "mock_agent", "interval": 4, "action": "reset"},
                "interval_4_reset",
            )
        baseline = self.baseline_setpoint_c or telemetry.current_cooling_setpoint_c
        requested = (
            baseline
            if stage == 0
            else baseline + 1.0
            if stage in {1, 2}
            else baseline + 5.0
        )
        if stage in {1, 2}:
            self.changed_setpoint_c = requested
        candidate = build_candidate(
            telemetry,
            actuator,
            requested,
            "mock_agent",
            reason=(
                "intentionally_invalid_phase8_fallback_test"
                if stage == 4
                else "deterministic_mock_interval"
            ),
            settings=self.settings,
        )
        return ProviderDecision(
            "apply",
            candidate,
            {
                "source": "mock_agent",
                "interval": stage + 1,
                "requested_setpoint_c": requested,
                "intentionally_invalid": stage == 4,
            },
            f"interval_{stage + 1}",
        )

    def observe(self, setpoint_c: float, reset_active: bool) -> None:
        if (
            self.changed_setpoint_c is not None
            and abs(setpoint_c - self.changed_setpoint_c)
            <= self.settings.verification_tolerance_c
        ):
            self.change_observed = True
        if (
            reset_active
            and self.baseline_setpoint_c is not None
            and abs(setpoint_c - self.baseline_setpoint_c)
            <= self.settings.verification_tolerance_c
        ):
            self.reset_observed = True
            if self._stage >= 5:
                self.fallback_observed = True
                self.complete = self.change_observed


class Phase7ProposalProvider:
    """Normalize a live-context advisory or continue with a safe fallback."""

    def __init__(
        self,
        proposal: Any | None,
        validation: Any | None = None,
        settings: Phase8Settings = PHASE8_SETTINGS,
        *,
        live_context: Any | None = None,
        llm_called: bool = True,
        llm_completed: bool = True,
        llm_error_code: str | None = None,
        llm_error_message: str | None = None,
        llm_raw_content: str = "",
        llm_messages: list[dict[str, str]] | None = None,
        minimum_confidence: float = 0.3,
    ) -> None:
        self.proposal = proposal
        self.validation = validation
        self.settings = settings
        self.live_context = live_context
        self.llm_called = llm_called
        self.llm_completed = llm_completed
        self.llm_error_code = llm_error_code
        self.llm_error_message = llm_error_message
        self.llm_raw_content = llm_raw_content
        self.llm_messages = llm_messages or []
        self.minimum_confidence = minimum_confidence
        self.complete = False
        self.required_intervals = (
            settings.llm_assisted_validation_intervals
        )
        self._stage = 0
        self._decision_hour: tuple[int, int] | None = None
        self.baseline_setpoint_c: float | None = None
        self.changed_setpoint_c: float | None = None
        self.raw_llm_requested_setpoint_c: float | None = None
        self.normalized_requested_setpoint_c: float | None = None
        self.normalization_applied = False
        self.normalization_reason: str | None = None
        self.fallback_reason: str | None = None
        self.fallback_used = False
        self.fallback_target_c: float | None = None
        self.llm_action_used = False
        self.change_observed = False
        self.reset_observed = False
        self.fallback_observed = False

    @property
    def intervals_completed(self) -> int:
        return self._stage

    def _proposal_value(self, name: str, default: Any = None) -> Any:
        return getattr(self.proposal, name, default)

    def _first_action(
        self,
        telemetry: RuntimeTelemetrySnapshot,
        actuator: ActuatorDescriptor,
    ) -> ProviderDecision:
        live = telemetry.current_cooling_setpoint_c
        self.baseline_setpoint_c = live
        raw = self._proposal_value("proposed_setpoint_c")
        if isinstance(raw, (int, float)) and math.isfinite(float(raw)):
            self.raw_llm_requested_setpoint_c = float(raw)
        lower = max(
            self.settings.minimum_cooling_setpoint_c,
            live - self.settings.maximum_setpoint_change_c,
        )
        upper = min(
            self.settings.maximum_cooling_setpoint_c,
            live + self.settings.maximum_setpoint_change_c,
        )
        normalization_notes: list[str] = []
        rejection_reasons: list[str] = []
        if self.raw_llm_requested_setpoint_c is not None:
            normalized = min(
                max(self.raw_llm_requested_setpoint_c, lower), upper
            )
            self.normalized_requested_setpoint_c = normalized
            if abs(normalized - self.raw_llm_requested_setpoint_c) > 1e-9:
                self.normalization_applied = True
                normalization_notes.append(
                    "CLAMPED_TO_LIVE_SETPOINT_AND_DELTA_BOUNDS"
                )
        else:
            normalized = None
            rejection_reasons.append("MISSING_OR_INVALID_SETPOINT")

        proposal_zone = self._proposal_value("energyplus_zone_name")
        proposal_current = self._proposal_value("current_setpoint_c")
        objective = self._proposal_value("objective")
        confidence = self._proposal_value("confidence")
        if self.proposal is None:
            rejection_reasons.append(
                self.llm_error_code or "MISSING_DECISION"
            )
        if self.validation is not None and getattr(
            self.validation, "valid", False
        ) is not True:
            rejection_reasons.append("PHASE7_PROPOSAL_INVALID")
        if proposal_zone != self.settings.controlled_zone:
            rejection_reasons.append("INVALID_ZONE")
        if (
            isinstance(proposal_current, (int, float))
            and abs(float(proposal_current) - live)
            > self.settings.verification_tolerance_c
        ):
            rejection_reasons.append(
                "PROPOSAL_CURRENT_SETPOINT_MISMATCH"
            )
        if (
            not isinstance(confidence, (int, float))
            or float(confidence) < self.minimum_confidence
        ):
            rejection_reasons.append("CONFIDENCE_BELOW_THRESHOLD")
        if objective not in {
            "reduce_energy",
            "reduce_peak_demand",
            "maintain_comfort",
        }:
            rejection_reasons.append("UNSUPPORTED_DECISION")
        if (
            normalized is not None
            and objective in {"reduce_energy", "reduce_peak_demand"}
            and normalized < live - 1e-9
        ):
            rejection_reasons.append(
                "ENERGY_REDUCTION_DIRECTION_INVALID"
            )

        use_llm = not rejection_reasons and normalized is not None
        if use_llm:
            selected = normalized
            source: Literal["phase7_llm", "fallback"] = "phase7_llm"
            self.llm_action_used = True
            proposal_source = "llm_runtime_decision"
        else:
            self.fallback_used = True
            self.fallback_reason = ";".join(
                dict.fromkeys(rejection_reasons)
            )
            comfort_sufficient = bool(
                getattr(
                    self.live_context,
                    "comfort_evidence_sufficient",
                    False,
                )
                or (
                    telemetry.occupancy is not None
                    and telemetry.occupancy <= 0.0
                )
            )
            selected = live
            if comfort_sufficient:
                selected = min(
                    live + 0.5,
                    self.settings.maximum_cooling_setpoint_c,
                    live + self.settings.maximum_setpoint_change_c,
                )
            selected = max(
                self.settings.minimum_cooling_setpoint_c,
                min(selected, self.settings.maximum_cooling_setpoint_c),
            )
            self.fallback_target_c = selected
            source = "fallback"
            proposal_source = "deterministic_runtime_fallback"
        self.changed_setpoint_c = selected
        self.normalization_reason = (
            ";".join(
                dict.fromkeys(
                    normalization_notes + rejection_reasons
                )
            )
            if normalization_notes or rejection_reasons
            else "WITHIN_LIVE_SETPOINT_AND_DELTA_BOUNDS"
        )
        candidate = build_candidate(
            telemetry,
            actuator,
            selected,
            source,
            proposal_id=self._proposal_value("proposal_id"),
            phase7_validated=True if source == "phase7_llm" else None,
            confidence=(
                float(confidence)
                if isinstance(confidence, (int, float))
                else None
            ),
            settings=self.settings,
        )
        diagnostics = {
            "source": "phase7_llm_adapter",
            "interval": 1,
            "zone": self.settings.controlled_zone,
            "live_current_setpoint_c": live,
            "proposal_current_setpoint_c": proposal_current,
            "raw_llm_requested_setpoint_c": (
                self.raw_llm_requested_setpoint_c
            ),
            "normalized_requested_setpoint_c": (
                self.normalized_requested_setpoint_c
            ),
            "normalization_applied": self.normalization_applied,
            "normalization_reason": self.normalization_reason,
            "selected_action_setpoint_c": selected,
            "fallback_target_c": self.fallback_target_c,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "proposal_source": proposal_source,
            "llm_called": self.llm_called,
            "llm_completed": self.llm_completed,
            "llm_action_used": self.llm_action_used,
            "llm_error_code": self.llm_error_code,
            "llm_error_message": self.llm_error_message,
            "llm_raw_content": self.llm_raw_content,
            "llm_proposal": (
                self.proposal.model_dump(mode="json")
                if hasattr(self.proposal, "model_dump")
                else None
            ),
            "compact_llm_messages": self.llm_messages,
            "objective": objective,
            "advisory_only": True,
        }
        return ProviderDecision(
            "apply",
            candidate,
            diagnostics,
            "interval_1_llm_or_runtime_fallback",
            self.fallback_reason,
        )

    def next_decision(
        self,
        telemetry: RuntimeTelemetrySnapshot,
        actuator: ActuatorDescriptor,
    ) -> ProviderDecision | None:
        stamp = telemetry.simulation_timestamp
        hour_key = (stamp.timetuple().tm_yday, stamp.hour)
        if self.complete or hour_key == self._decision_hour:
            return None
        self._decision_hour = hour_key
        if self._stage == 0:
            self._stage = 1
            return self._first_action(telemetry, actuator)
        if self._stage < self.required_intervals - 1:
            self._stage += 1
            target = (
                self.changed_setpoint_c
                if self.changed_setpoint_c is not None
                else telemetry.current_cooling_setpoint_c
            )
            source = "fallback" if self.fallback_used else "phase7_llm"
            candidate = build_candidate(
                telemetry,
                actuator,
                target,
                source,
                proposal_id=self._proposal_value("proposal_id"),
                phase7_validated=(
                    True if source == "phase7_llm" else None
                ),
                confidence=self._proposal_value("confidence"),
                settings=self.settings,
            )
            return ProviderDecision(
                "apply",
                candidate,
                {
                    "source": "phase7_llm_adapter",
                    "interval": self._stage,
                    "action": "maintain_selected_action",
                    "selected_action_setpoint_c": target,
                    "fallback_used": self.fallback_used,
                    "fallback_reason": self.fallback_reason,
                },
                f"interval_{self._stage}_maintain",
                self.fallback_reason if self.fallback_used else None,
            )
        if self._stage == self.required_intervals - 1:
            self._stage += 1
            return ProviderDecision(
                "reset",
                None,
                {
                    "source": "phase7_llm_adapter",
                    "interval": self._stage,
                    "action": "reset_actuator",
                    "fallback_used": self.fallback_used,
                },
                f"interval_{self._stage}_reset",
            )
        return None

    def validation_fallback(
        self,
        telemetry: RuntimeTelemetrySnapshot,
        actuator: ActuatorDescriptor,
        validation_errors: list[str],
    ) -> ExecutableActionCandidate:
        """Build a live, conservative candidate after validator rejection."""
        live = telemetry.current_cooling_setpoint_c
        comfort_sufficient = bool(
            getattr(
                self.live_context,
                "comfort_evidence_sufficient",
                False,
            )
            or (
                telemetry.occupancy is not None
                and telemetry.occupancy <= 0.0
            )
        )
        target = live
        if comfort_sufficient:
            target = min(
                live + 0.5,
                live + self.settings.maximum_setpoint_change_c,
                self.settings.maximum_cooling_setpoint_c,
            )
        if telemetry.current_heating_setpoint_c is not None:
            target = max(
                target,
                telemetry.current_heating_setpoint_c
                + self.settings.minimum_heating_cooling_deadband_c,
            )
        target = min(
            max(target, self.settings.minimum_cooling_setpoint_c),
            self.settings.maximum_cooling_setpoint_c,
            live + self.settings.maximum_setpoint_change_c,
        )
        self.fallback_used = True
        self.llm_action_used = False
        self.fallback_target_c = target
        self.changed_setpoint_c = target
        suffix = "NORMALIZED_TARGET_VALIDATION_REJECTED:" + ",".join(
            validation_errors
        )
        self.fallback_reason = ";".join(
            item
            for item in (self.fallback_reason, suffix)
            if item
        )
        return build_candidate(
            telemetry,
            actuator,
            target,
            "fallback",
            proposal_id=self._proposal_value("proposal_id"),
            confidence=self._proposal_value("confidence"),
            settings=self.settings,
        )

    def observe(self, setpoint_c: float, reset_active: bool) -> None:
        if (
            self.changed_setpoint_c is not None
            and abs(setpoint_c - self.changed_setpoint_c)
            <= self.settings.verification_tolerance_c
        ):
            if (
                self.baseline_setpoint_c is not None
                and abs(setpoint_c - self.baseline_setpoint_c)
                > self.settings.verification_tolerance_c
            ):
                self.change_observed = True
            if self.fallback_used:
                self.fallback_observed = True
        if (
            self._stage >= self.required_intervals
            and reset_active
            and self.baseline_setpoint_c is not None
            and abs(setpoint_c - self.baseline_setpoint_c)
            <= self.settings.verification_tolerance_c
        ):
            self.reset_observed = True
            self.complete = True


__all__ = [
    "ActionProvider",
    "ManualActionProvider",
    "MockActionProvider",
    "Phase7ProposalProvider",
    "ProviderDecision",
    "build_candidate",
]
