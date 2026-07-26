import pytest
from pydantic import ValidationError

from llm.schemas import ControlProposal, LLMDecision
from scripts.test_phase7_agent import valid_decision, valid_proposal


def test_valid_proposal():
    proposal = ControlProposal.model_validate(valid_proposal())
    assert proposal.energyplus_zone_name == "SPACE1-1"


def test_missing_evidence_rejected():
    data = valid_proposal()
    data["evidence"] = []
    with pytest.raises(ValidationError):
        ControlProposal.model_validate(data)


def test_invalid_confidence_rejected():
    data = valid_proposal()
    data["confidence"] = 1.2
    with pytest.raises(ValidationError):
        ControlProposal.model_validate(data)


def test_applied_true_rejected():
    data = valid_proposal()
    data["applied_to_energyplus"] = True
    with pytest.raises(ValidationError):
        ControlProposal.model_validate(data)


def test_multiple_zone_shape_rejected():
    data = valid_proposal()
    data["energyplus_zone_names"] = ["SPACE1-1", "SPACE2-1"]
    with pytest.raises(ValidationError):
        ControlProposal.model_validate(data)


def test_llm_decision_is_minimal_and_forbids_extra_fields():
    decision = LLMDecision.model_validate(valid_decision())
    assert decision.objective == "reduce_peak_demand"
    invalid = valid_decision()
    invalid["advisory_only"] = False
    with pytest.raises(ValidationError):
        LLMDecision.model_validate(invalid)
