import pytest
from pydantic import ValidationError

from safety.fault_injection import make_state
from safety.schemas import SafetyRuleResult


def test_phase9_state_is_strict_and_unified():
    state = make_state()
    assert state.zone_name == "SPACE1-1"
    assert state.indoor_temperature_c == 23.0
    with pytest.raises(ValidationError):
        state.__class__(**(state.model_dump() | {"unexpected": True}))


def test_rule_result_rejects_unknown_action():
    with pytest.raises(ValidationError):
        SafetyRuleResult(
            rule_id="X",
            passed=False,
            severity="error",
            message="invalid",
            action="execute",
        )
