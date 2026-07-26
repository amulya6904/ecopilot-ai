"""Final-authority deterministic validation of executable runtime actions."""

from dataclasses import dataclass
from datetime import datetime
import time
import uuid

from .handles import HandleRegistry
from .schemas import (
    ActionValidationResult,
    ExecutableActionCandidate,
    RuntimeTelemetrySnapshot,
)
from .settings import PHASE8_SETTINGS, Phase8Settings


RUNTIME_VALIDATOR_VERSION = "phase8-runtime-validator-v1"


@dataclass(frozen=True)
class RuntimeValidationContext:
    now: datetime
    telemetry: RuntimeTelemetrySnapshot | None
    handles: HandleRegistry
    actuator_identifier: str
    control_enabled: bool
    active_action_id: str | None = None
    last_application_at: datetime | None = None
    pmv_available: bool = False


def validate_action_candidate(
    candidate: ExecutableActionCandidate,
    context: RuntimeValidationContext,
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> ActionValidationResult:
    started = time.perf_counter()
    errors: list[str] = []
    warnings: list[str] = []
    if not context.control_enabled:
        errors.append("CONTROL_EXECUTION_DISABLED")
    if candidate.source_type == "phase7_llm" and candidate.phase7_validated is not True:
        errors.append("PHASE7_PROPOSAL_NOT_VALIDATED")
    if candidate.zone_name != settings.controlled_zone:
        errors.append("UNKNOWN_OR_UNCONTROLLED_ZONE")
    if "plenum" in candidate.zone_name.casefold():
        errors.append("PLENUM_CONTROL_REJECTED")
    if candidate.actuator_identifier != context.actuator_identifier:
        errors.append("ACTUATOR_ZONE_MISMATCH")
    if context.handles.cooling_actuator == -1:
        errors.append("INVALID_ACTUATOR")
    telemetry = context.telemetry
    if telemetry is None or not telemetry.handles_ready:
        errors.append("MISSING_TELEMETRY")
    else:
        if abs(
            candidate.current_value_c
            - telemetry.current_cooling_setpoint_c
        ) > settings.verification_tolerance_c:
            errors.append("CURRENT_SETPOINT_MISMATCH")
        if (
            telemetry.current_heating_setpoint_c is not None
            and candidate.requested_value_c
            < telemetry.current_heating_setpoint_c
            + settings.minimum_heating_cooling_deadband_c
        ):
            errors.append("DEADBAND_VIOLATION")
        if (
            telemetry.occupancy is None
            or telemetry.zone_temperature_c
            > settings.maximum_cooling_setpoint_c
        ):
            warnings.append("COMFORT_TELEMETRY_UNCERTAINTY")
    if context.now > candidate.expires_at:
        errors.append("ACTION_STALE")
    if not (
        candidate.effective_from
        <= context.now
        <= candidate.effective_until
    ):
        errors.append("OUTSIDE_EFFECTIVE_WINDOW")
    if context.active_action_id not in {None, candidate.action_id}:
        errors.append("CONFLICTING_ACTIVE_ACTION")
    if (
        context.last_application_at is not None
        and context.active_action_id not in {None, candidate.action_id}
        and (
            context.now - context.last_application_at
        ).total_seconds() < settings.minimum_hold_minutes * 60
    ):
        errors.append("MINIMUM_HOLD_NOT_MET")
    requested = candidate.requested_value_c
    approved = requested
    outcome = "approved"
    if not (
        settings.minimum_cooling_setpoint_c
        <= requested
        <= settings.maximum_cooling_setpoint_c
    ):
        errors.append("SETPOINT_OUT_OF_BOUNDS")
    delta = requested - candidate.current_value_c
    if abs(delta) > settings.maximum_setpoint_change_c:
        errors.append("MAXIMUM_DELTA_EXCEEDED")
    if abs(delta) <= 1e-6 and not errors:
        outcome = "hold"
        approved = candidate.current_value_c
        warnings.append("NO_SETPOINT_CHANGE")
    if not context.pmv_available:
        warnings.append("PMV_UNAVAILABLE")
    risk = (
        "high"
        if errors or "COMFORT_TELEMETRY_UNCERTAINTY" in warnings
        else "medium"
        if not context.pmv_available
        else "low"
    )
    valid = not errors
    return ActionValidationResult(
        validation_id=f"validation-{uuid.uuid4().hex}",
        valid=valid,
        approved=valid,
        outcome=outcome if valid else "rejected",
        requested_value_c=requested,
        approved_value_c=approved if valid else None,
        errors=errors,
        warnings=warnings,
        risk_level=risk,
        validator_version=RUNTIME_VALIDATOR_VERSION,
        fallback_required=not valid,
        validation_latency_ms=(time.perf_counter() - started) * 1000,
    )


__all__ = [
    "RUNTIME_VALIDATOR_VERSION",
    "RuntimeValidationContext",
    "validate_action_candidate",
]
