from copy import deepcopy

import pytest

from llm.schemas import ControlProposal
from llm.settings import LLM_SETTINGS
from llm.validator import (
    LOW_COMFORT_CONFIDENCE,
    UNSUPPORTED_OPTIMALITY_CLAIM,
    validate_proposal,
)
from llm.decision import assemble_control_proposal
from llm.schemas import LLMDecision
from scripts.test_phase7_agent import mock_tool_data, valid_decision, valid_proposal


def history(zone_role="primary_occupied", included=True):
    events = []
    for name in (
        "get_official_baseline_summary", "get_facility_summary", "list_zones",
        "get_comfort_summary", "get_thermostat_adherence",
    ):
        response = mock_tool_data(name)
        if name == "list_zones":
            response["data"]["zones"][0]["role"] = zone_role
            response["data"]["zones"][0]["included_in_comfort"] = included
        events.append({"tool": name, "success": True, "response": response})
    return events


def validate(data=None, events=None):
    proposal = ControlProposal.model_validate(data or valid_proposal())
    return validate_proposal(proposal, events or history(), LLM_SETTINGS)


def test_valid_occupied_zone():
    assert validate().valid


@pytest.mark.parametrize("role,included", [("plenum", False), ("primary_occupied", False)])
def test_noncomfort_zone_rejected(role, included):
    result = validate(events=history(role, included))
    assert not result.valid


def test_unknown_zone_rejected():
    data = valid_proposal()
    data["energyplus_zone_name"] = "UNKNOWN"
    assert not validate(data).valid


@pytest.mark.parametrize("proposed,delta", [(29.0, 7.0), (24.5, 2.5)])
def test_bounds_and_maximum_delta(proposed, delta):
    data = valid_proposal()
    data["proposed_setpoint_c"], data["setpoint_change_c"] = proposed, delta
    assert not validate(data).valid


def test_pmv_hallucination_rejected():
    data = valid_proposal()
    data["comfort_assessment"]["pmv_available"] = True
    data["comfort_assessment"]["pmv_compliance_percent"] = 100.0
    assert not validate(data).valid


def test_missing_evidence_rejected():
    data = valid_proposal()
    data["evidence"] = data["evidence"][1:]
    assert not validate(data).valid


def test_current_setpoint_mismatch_rejected():
    data = valid_proposal()
    data["current_setpoint_c"] = 21.0
    data["setpoint_change_c"] = 2.0
    assert not validate(data).valid


def test_flags_are_schema_enforced():
    data = valid_proposal()
    data["advisory_only"] = False
    with pytest.raises(Exception):
        ControlProposal.model_validate(data)


def test_zero_delta_is_assembled_as_low_confidence_hold():
    events = history()
    events[3]["response"]["data"]["temperature_compliance_percent"] = 23.2
    decision = LLMDecision(
        energyplus_zone_name="SPACE1-1",
        proposed_setpoint_c=22.0,
        objective="maintain_comfort",
        confidence=0.95,
        reason="The current value is already optimal.",
    )
    proposal = assemble_control_proposal(decision, events, LLM_SETTINGS)
    assert proposal.decision_type == "hold_current_setpoint"
    assert proposal.setpoint_change_c == 0
    assert proposal.confidence <= 0.45
    assert "optimal" not in proposal.reason.casefold()
    assert validate_proposal(proposal, events, LLM_SETTINGS).valid


def test_unsupported_optimality_claim_is_rejected():
    data = valid_proposal()
    data["reason"] = "This is the best and optimal setpoint."
    result = validate(data)
    assert not result.valid
    assert any(
        UNSUPPORTED_OPTIMALITY_CLAIM in error
        for error in result.validation_errors
    )


def test_low_comfort_warning_and_confidence_cap():
    data = valid_proposal()
    data["confidence"] = 0.95
    events = history()
    events[3]["response"]["data"]["temperature_compliance_percent"] = 23.2
    data["comfort_assessment"]["temperature_compliance_percent"] = 23.2
    result = validate(data, events)
    assert not result.valid
    assert any(
        LOW_COMFORT_CONFIDENCE in warning
        for warning in result.validation_warnings
    )


def test_pmv_unavailable_is_preserved():
    proposal = assemble_control_proposal(
        LLMDecision.model_validate(valid_decision() | {
            "confidence": 0.4,
        }),
        history(),
        LLM_SETTINGS,
    )
    assert proposal.comfort_assessment.pmv_available is False
    assert proposal.comfort_assessment.pmv_compliance_percent is None
