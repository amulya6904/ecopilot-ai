from dataclasses import replace

from safety.deadband import evaluate_deadband
from safety.fault_injection import make_state
from safety.settings import SAFETY_SETTINGS


def test_deadband_valid_violation_and_clamp():
    rules, approved = evaluate_deadband(
        make_state(heating_setpoint_c=20.0), 22.0
    )
    assert rules[-1].passed and approved == 22.0
    rules, approved = evaluate_deadband(
        make_state(heating_setpoint_c=22.5), 23.0
    )
    assert not rules[-1].passed and approved == 23.5


def test_missing_heating_uses_explicit_proxy_or_fallback():
    rules, _ = evaluate_deadband(
        make_state(heating_setpoint_c=None), 22.0
    )
    assert rules[0].rule_id == "HEATING_SETPOINT_PROXY_USED"
    no_proxy = replace(SAFETY_SETTINGS, allow_baseline_heating_proxy=False)
    rules, _ = evaluate_deadband(
        make_state(heating_setpoint_c=None), 22.0, no_proxy
    )
    assert rules[0].action == "fallback"
