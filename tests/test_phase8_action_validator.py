from datetime import timedelta

from energyplus.runtime_control.action_provider import build_candidate
from energyplus.runtime_control.validator import (
    RuntimeValidationContext,
    validate_action_candidate,
)
from tests.phase8_helpers import ACTUATOR, ready_handles, telemetry


def context(now):
    return RuntimeValidationContext(
        now=now, telemetry=telemetry(), handles=ready_handles(),
        actuator_identifier=ACTUATOR.identifier, control_enabled=True,
    )


def test_valid_action_is_approved():
    item = build_candidate(telemetry(), ACTUATOR, 23.0, "manual")
    assert validate_action_candidate(
        item, context(item.effective_from)
    ).approved


def test_stale_action_is_rejected():
    item = build_candidate(telemetry(), ACTUATOR, 23.0, "manual")
    result = validate_action_candidate(
        item, context(item.expires_at + timedelta(minutes=1))
    )
    assert "ACTION_STALE" in result.errors
