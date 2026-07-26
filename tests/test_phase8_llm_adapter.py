from types import SimpleNamespace

from energyplus.runtime_control.action_provider import Phase7ProposalProvider
from energyplus.runtime_control.llm_adapter import (
    LiveRuntimeContext,
    build_runtime_llm_messages,
)
from energyplus.runtime_control.validator import (
    RuntimeValidationContext,
    validate_action_candidate,
)
from tests.phase8_helpers import ACTUATOR, ready_handles, telemetry


class Proposal:
    proposed_setpoint_c = 22.0
    proposal_id = "proposal-1"
    confidence = 0.4
    energyplus_zone_name = "SPACE1-1"
    current_setpoint_c = 22.0
    objective = "reduce_energy"
    def model_dump(self, mode): return {"proposal_id": self.proposal_id}


def live_context(current=27.0, comfort=True):
    return LiveRuntimeContext(
        zone="SPACE1-1",
        live_current_setpoint_c=current,
        minimum_setpoint_c=20.0,
        maximum_setpoint_c=28.0,
        maximum_delta_c=1.0,
        zone_temperature_c=21.0,
        heating_setpoint_c=16.0,
        occupancy=0.0,
        outdoor_temperature_c=-5.0,
        comfort_evidence_sufficient=comfort,
        pmv_available=False,
        objective="reduce_energy",
        advisory_only=True,
        actuator_identifier=ACTUATOR.identifier,
    )


def test_compact_request_uses_live_runtime_context():
    messages = build_runtime_llm_messages(live_context())
    assert len(messages) == 2
    assert '"zone":"SPACE1-1"' in messages[1]["content"]
    assert '"live_current_setpoint_c":27.0' in messages[1]["content"]
    assert '"maximum_delta_c":1.0' in messages[1]["content"]
    assert "advisory_only_constraints" in messages[1]["content"]


def test_stale_phase7_current_is_rejected_and_live_fallback_is_used():
    provider = Phase7ProposalProvider(
        Proposal(),
        SimpleNamespace(valid=True),
        live_context=live_context(),
    )
    decision = provider.next_decision(telemetry(27.0, 0), ACTUATOR)
    assert provider.raw_llm_requested_setpoint_c == 22.0
    assert provider.normalized_requested_setpoint_c == 26.0
    assert provider.normalization_applied
    assert "PROPOSAL_CURRENT_SETPOINT_MISMATCH" in provider.fallback_reason
    assert decision.candidate.source_type == "fallback"
    assert decision.candidate.current_value_c == 27.0
    assert decision.candidate.requested_value_c == 27.5
    assert decision.candidate.requested_delta_c <= 0.5
    assert decision.proposal["raw_llm_requested_setpoint_c"] == 22.0
    assert decision.proposal["normalized_requested_setpoint_c"] == 26.0


def test_unsafe_raw_target_is_clamped_to_live_delta_bounds():
    proposal = SimpleNamespace(
        proposed_setpoint_c=40.0,
        proposal_id="proposal-high",
        confidence=0.6,
        energyplus_zone_name="SPACE1-1",
        objective="reduce_energy",
        model_dump=lambda mode: {"proposed_setpoint_c": 40.0},
    )
    provider = Phase7ProposalProvider(
        proposal, None, live_context=live_context()
    )
    decision = provider.next_decision(telemetry(27.0, 0), ACTUATOR)
    assert provider.normalized_requested_setpoint_c == 28.0
    assert provider.normalization_applied
    assert decision.candidate.requested_delta_c == 1.0
    assert provider.llm_action_used


def test_failed_llm_fallback_respects_bounds_and_insufficient_comfort_holds():
    provider = Phase7ProposalProvider(
        None,
        None,
        live_context=live_context(28.0, comfort=False),
        llm_called=True,
        llm_completed=False,
        llm_error_code="LLM_TIMEOUT",
    )
    decision = provider.next_decision(telemetry(28.0, 0), ACTUATOR)
    assert provider.fallback_used
    assert provider.fallback_target_c == 28.0
    assert decision.candidate.requested_delta_c == 0.0
    assert 20.0 <= decision.candidate.requested_value_c <= 28.0


def test_rejected_llm_continues_multiple_intervals_and_resets():
    provider = Phase7ProposalProvider(
        Proposal(),
        SimpleNamespace(valid=False),
        live_context=live_context(),
    )
    first = provider.next_decision(telemetry(27.0, 0), ACTUATOR)
    assert first.candidate.source_type == "fallback"
    provider.observe(27.5, False)
    second = provider.next_decision(telemetry(27.5, 1), ACTUATOR)
    assert second.kind == "apply"
    assert second.candidate.requested_value_c == 27.5
    provider.observe(27.5, False)
    third = provider.next_decision(telemetry(27.5, 2), ACTUATOR)
    assert third.kind == "reset"
    provider.observe(27.0, True)
    assert provider.intervals_completed == 3
    assert provider.fallback_observed
    assert provider.reset_observed
    assert provider.complete


def test_validator_rejection_fallback_reaches_approved_write_candidate():
    provider = Phase7ProposalProvider(
        Proposal(), None, live_context=live_context()
    )
    live = telemetry(27.0, 0)
    fallback = provider.validation_fallback(
        live, ACTUATOR, ["CURRENT_SETPOINT_MISMATCH"]
    )
    result = validate_action_candidate(
        fallback,
        RuntimeValidationContext(
            now=live.simulation_timestamp,
            telemetry=live,
            handles=ready_handles(),
            actuator_identifier=ACTUATOR.identifier,
            control_enabled=True,
        ),
    )
    assert result.approved
    assert fallback.source_type == "fallback"
    assert fallback.requested_delta_c == 0.5
    assert "NORMALIZED_TARGET_VALIDATION_REJECTED" in provider.fallback_reason
